"""Gauge reading CV — REAL OpenCV pipeline: adaptive threshold + HoughCircles + needle angle → value.

Offline-first, no cloud. Deterministic, tested with synthetic images.

Pipeline:
  1) grayscale + median blur + adaptiveThreshold (handles dust/glare)
  2) HoughCircles to locate dial rim (robust centre/radius)
  3) mask outside dial, Canny + HoughLinesP to find needle
  4) angle from centre → value via dial geometry (min_angle→max_angle clockwise)
  5) confidence from circle certainty + line strength + radius conformity
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class GaugeConfig:
    """Dial geometry — all angles in degrees, 0° = +x (right), 90° = +y (down) in image coords."""

    min_value: float = 0.0
    max_value: float = 10.0
    # needle at min_value sits at min_angle_deg; at max_value at max_angle_deg, swept clockwise
    min_angle_deg: float = 135.0
    max_angle_deg: float = 45.0  # 135→45 clockwise = 270° span
    # Hough tuning
    blur_ksize: int = 5
    adaptive_block: int = 31
    adaptive_c: int = 5
    canny_low: int = 50
    canny_high: int = 150

    @property
    def span_deg(self) -> float:
        """Clockwise span from min to max (0-360)."""
        return (self.min_angle_deg - self.max_angle_deg) % 360.0 or 360.0

    def angle_to_value(self, angle_deg: float) -> float:
        """Map needle angle → value. Angle is 0-360 (0=right, 90=down)."""
        # signed clockwise distance from min_angle to angle
        cw = (self.min_angle_deg - angle_deg) % 360.0
        # clamp to span (if needle slightly outside dial, clamp)
        cw = max(0.0, min(cw, self.span_deg))
        frac = cw / self.span_deg if self.span_deg else 0.0
        return self.min_value + frac * (self.max_value - self.min_value)

    def value_to_angle(self, value: float) -> float:
        frac = (value - self.min_value) / (self.max_value - self.min_value) if self.max_value != self.min_value else 0.0
        frac = max(0.0, min(1.0, frac))
        return (self.min_angle_deg - frac * self.span_deg) % 360.0


@dataclass(frozen=True, slots=True)
class GaugeResult:
    value: float
    angle_deg: float
    confidence: float
    latency_ms: float
    centre: tuple[int, int]
    radius: int
    debug: dict


def _angle_deg(dx: float, dy: float) -> float:
    # image y is down, so atan2(dy, dx) matches 0=right 90=down
    return math.degrees(math.atan2(dy, dx)) % 360.0


def _clockwise_span(a: float, b: float) -> float:
    return (a - b) % 360.0


def read_gauge(image: np.ndarray, config: GaugeConfig | None = None) -> GaugeResult:
    """REAL gauge reader. image: BGR or gray uint8. Returns GaugeResult (value + confidence).

    Raises ValueError if image is None/empty. Never raises on no-detection — returns
    confidence 0 with best-effort fallback centre.
    """
    t0 = time.perf_counter()
    if image is None or image.size == 0:
        raise ValueError("empty image")
    cfg = config or GaugeConfig()

    # ——— 1. preprocess ———
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    # median blur preserves edges better than Gaussian for dust
    k = cfg.blur_ksize if cfg.blur_ksize % 2 == 1 else cfg.blur_ksize + 1
    blurred = cv2.medianBlur(gray, k)
    # adaptive threshold handles glare/vignetting
    block = cfg.adaptive_block if cfg.adaptive_block % 2 == 1 else cfg.adaptive_block + 1
    block = max(3, block)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block, cfg.adaptive_c
    )

    h, w = gray.shape[:2]
    fallback_centre = (w // 2, h // 2)
    fallback_radius = min(h, w) // 2 - 4

    # ——— 2. dial circle ——— (use blurred gray for HoughCircles; thresh kept for masking)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=min(h, w) // 2,
        param1=cfg.canny_high,
        param2=90,
        minRadius=int(min(h, w) * 0.30),
        maxRadius=int(min(h, w) * 0.55),
    )
    # second-chance with lower accumulator threshold for thin synthetic rim / noisy field
    if circles is None or len(circles[0]) == 0:
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=min(h, w) // 2,
            param1=cfg.canny_high,
            param2=55,
            minRadius=int(min(h, w) * 0.30),
            maxRadius=int(min(h, w) * 0.55),
        )
    if circles is not None and len(circles[0]) > 0:
        # choose circle closest to image centre and with most edge support
        cx0, cy0 = w / 2, h / 2
        best = min(circles[0], key=lambda c: math.hypot(c[0] - cx0, c[1] - cy0))
        cx, cy, r = int(round(best[0])), int(round(best[1])), int(round(best[2]))
        circle_conf = 0.85
        # boost confidence if radius is well-formed (not near limits) and centred
        centredness = 1.0 - min(1.0, math.hypot(cx - cx0, cy - cy0) / (min(h, w) * 0.12))
        circle_conf = 0.70 + 0.25 * centredness
    else:
        # fallback: assume dial fills frame (synthetic/test path) — try contour-based radius
        # fit minEnclosingCircle to outer threshold contour as last resort
        try:
            # use adaptive thresh outer components
            cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if cnts:
                # largest by area likely the rim
                c = max(cnts, key=cv2.contourArea)
                (x0, y0), rad = cv2.minEnclosingCircle(c)
                # sanity: radius must be big
                if rad > min(h, w) * 0.25 and cv2.contourArea(c) > (h * w) * 0.12:
                    cx, cy, r = int(round(x0)), int(round(y0)), int(round(rad))
                    circle_conf = 0.55
                else:
                    cx, cy, r = fallback_centre[0], fallback_centre[1], fallback_radius
                    circle_conf = 0.40
            else:
                cx, cy, r = fallback_centre[0], fallback_centre[1], fallback_radius
                circle_conf = 0.40
        except Exception:
            cx, cy, r = fallback_centre[0], fallback_centre[1], fallback_radius
            circle_conf = 0.40

    # ——— 3. needle detection ———
    # mask to dial interior (shrink a few px to remove rim)
    mask = np.zeros_like(gray)
    cv2.circle(mask, (cx, cy), max(8, r - 3), 255, -1)
    # inner hole mask to suppress hub glare (remove very centre)
    cv2.circle(mask, (cx, cy), max(6, r // 10), 0, -1)
    masked_gray = cv2.bitwise_and(gray, gray, mask=mask)
    # Canny on masked gray; more sensitive thresholds for thin needle
    edges = cv2.Canny(masked_gray, cfg.canny_low, cfg.canny_high)
    # dilate slightly to connect needle fragments
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    # mask edges to dial interior again (dilation leaks)
    edges = cv2.bitwise_and(edges, edges, mask=mask)

    lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi / 180, threshold=40, minLineLength=r * 0.45, maxLineGap=8)

    angle_deg: float | None = None
    line_strength = 0.0
    best_len = 0.0

    if lines is not None:
        # score each line by: length + distance of one endpoint near centre + coverage of radius
        best_score = -1.0
        best_angle = None
        for seg in lines:
            x1, y1, x2, y2 = seg[0]
            length = math.hypot(x2 - x1, y2 - y1)
            # which endpoint is nearer centre = hub; other = tip
            d1 = math.hypot(x1 - cx, y1 - cy)
            d2 = math.hypot(x2 - cx, y2 - cy)
            hub_near = min(d1, d2)
            tip_far = max(d1, d2)
            # prefer segments that start near centre and extend toward rim
            hub_score = max(0.0, 1.0 - hub_near / (r * 0.35))
            radial_score = min(1.0, tip_far / (r * 0.92))
            # direction bonus — longer + radial is better
            score = length * (0.5 + 0.5 * hub_score) * (0.6 + 0.4 * radial_score)
            if score > best_score:
                best_score = score
                # tip is far endpoint
                if d2 > d1:
                    tip_x, tip_y = x2, y2
                else:
                    tip_x, tip_y = x1, y1
                best_angle = _angle_deg(tip_x - cx, tip_y - cy)
                best_len = length
                line_strength = min(1.0, best_score / (r * 1.2))

        angle_deg = best_angle

    # fallback if no lines: try contour of thresholded needle blob
    if angle_deg is None:
        # thresholded needle is white line; find contours
        # erode mask to avoid rim
        small_mask = np.zeros_like(gray)
        cv2.circle(small_mask, (cx, cy), max(10, r - 6), 255, -1)
        cv2.circle(small_mask, (cx, cy), max(6, r // 10), 0, -1)
        thresh_masked = cv2.bitwise_and(thresh, thresh, mask=small_mask)
        # keep only long thin component (open to remove specks)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        opened = cv2.morphologyEx(thresh_masked, cv2.MORPH_OPEN, kernel, iterations=1)
        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # largest by area that is elongated
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:4]
            best_c = None
            best_elong = 0.0
            for c in contours:
                area = cv2.contourArea(c)
                if area < r * 2:
                    continue
                # fit line
                vx, vy, x0, y0 = cv2.fitLine(c, cv2.DIST_L2, 0, 0.01, 0.01).flatten().tolist()
                # elongation approx: length / width via minEnclosing
                rect = cv2.minAreaRect(c)
                (rw, rh) = rect[1]
                if rw == 0 or rh == 0:
                    continue
                elong = max(rw, rh) / (min(rw, rh) + 1e-6)
                if elong > best_elong:
                    best_elong = elong
                    best_c = (vx, vy, x0, y0)
            if best_c is not None:
                vx, vy, x0, y0 = best_c
                # choose direction away from centre: pick point along line far from centre
                # project centre->line point
                # tip is along (vx,vy) away from centre
                # decide sign so tip is away from centre
                dot = vx * (x0 - cx) + vy * (y0 - cy)
                sx = 1 if dot >= 0 else -1
                tip_x = x0 + sx * vx * r * 0.6
                tip_y = y0 + sx * vy * r * 0.6
                angle_deg = _angle_deg(tip_x - cx, tip_y - cy)
                line_strength = min(1.0, best_elong / 8.0) * 0.7

    if angle_deg is None:
        # total failure — report mid-scale with 0 confidence (caller can mark BAD)
        angle_deg = (cfg.min_angle_deg - cfg.span_deg / 2) % 360.0
        confidence = 0.0
    else:
        # confidence: weighted circle + line, with small bonus for angle inside dial span
        cw = _clockwise_span(cfg.min_angle_deg, angle_deg)
        in_span = 1.0 if cw <= cfg.span_deg + 1e-6 else max(0.0, 1.0 - (cw - cfg.span_deg) / 30.0)
        confidence = 0.38 * circle_conf + 0.52 * line_strength + 0.10 * in_span
        confidence = max(0.0, min(1.0, confidence))

    value = cfg.angle_to_value(angle_deg)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    return GaugeResult(
        value=float(value),
        angle_deg=float(angle_deg % 360.0),
        confidence=float(max(0.0, min(1.0, confidence))),
        latency_ms=float(latency_ms),
        centre=(int(cx), int(cy)),
        radius=int(r),
        debug={
            "circle_conf": float(circle_conf),
            "line_strength": float(line_strength),
            "lines_found": int(0 if lines is None else len(lines)),
            "best_len": float(best_len),
            "span_deg": float(cfg.span_deg),
        },
    )


def gauge_quality(confidence: float) -> str:
    if confidence >= 0.72:
        return "good"
    if confidence >= 0.45:
        return "uncertain"
    return "bad"
