"""Camera-as-adapter — OpenCV gauge needle detection via Hough + perspective.

Pipeline:
  1) Perspective correction: detect gauge outer contour / ellipse → compute homography to frontal circle
  2) Circle detection: HoughCircles on grayscale+blur to find gauge face
  3) Needle detection: Canny + HoughLinesP to find dominant line through center
  4) Angle → value: map angle linearly to [min_value, max_value] via [min_angle, max_angle]

All frames are processed locally; only the derived `value` is emitted as a DefectEvent/NormalizedReading.
No image data leaves the adapter (type system enforces it — DefectEvent has no image field).

Config params:
  rtsp_url / video_path / image_path: source (one required for live; for tests we accept numpy array injection)
  calibration: {min_angle, max_angle, min_value, max_value, angle_offset}
  perspective: {src_points: [[x,y]*4], dst_size: int} — optional manual homography
  gauge: {radius_range: [min,max], dp, min_dist, param1, param2} — Hough tuning
  detection_interval_ms: int
"""
from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np  # type: ignore

from ...domain.events import Quality, NormalizedReading
from ...domain.models import AdapterConfig
from ..base import BaseAdapter

try:
    import cv2  # type: ignore

    _HAS_CV2 = True
except Exception:  # pragma: no cover
    _HAS_CV2 = False
    cv2 = None  # type: ignore


@dataclass
class GaugeCalibration:
    min_angle: float = -135.0  # degrees, needle at min_value
    max_angle: float = 135.0
    min_value: float = 0.0
    max_value: float = 100.0
    angle_offset: float = 0.0  # added to detected angle (mechanical offset)

    def angle_to_value(self, angle_deg: float) -> float:
        a = angle_deg + self.angle_offset
        # clamp to calibration range
        lo, hi = self.min_angle, self.max_angle
        if lo > hi:
            lo, hi = hi, lo
        a_clamped = max(lo, min(hi, a))
        span_angle = hi - lo
        if span_angle == 0:
            return self.min_value
        frac = (a_clamped - lo) / span_angle
        return self.min_value + frac * (self.max_value - self.min_value)


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as tl, tr, br, bl."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # tl
    rect[2] = pts[np.argmax(s)]  # br
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # tr
    rect[3] = pts[np.argmax(diff)]  # bl
    return rect


def perspective_correct(image: np.ndarray, src_points: Optional[np.ndarray] = None, dst_size: int = 400) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Warp image to frontal view.

    If src_points provided (4x2), uses them. Otherwise tries to auto-detect gauge contour.
    Returns (warped, M) where M is homography or None if no warp.
    """
    if not _HAS_CV2:
        return image, None
    h, w = image.shape[:2]
    if src_points is not None:
        src = _order_points(np.array(src_points, dtype="float32"))
        dst = np.array([[0, 0], [dst_size - 1, 0], [dst_size - 1, dst_size - 1], [0, dst_size - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(image, M, (dst_size, dst_size))
        return warped, M

    # Auto: find largest contour approx quad
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image, None
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    for cnt in contours[:3]:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(cnt) > (h * w * 0.02):
            src = _order_points(approx.reshape(4, 2).astype("float32"))
            dst = np.array([[0, 0], [dst_size - 1, 0], [dst_size - 1, dst_size - 1], [0, dst_size - 1]], dtype="float32")
            M = cv2.getPerspectiveTransform(src, dst)
            warped = cv2.warpPerspective(image, M, (dst_size, dst_size))
            return warped, M
    return image, None


def detect_circle(image: np.ndarray, dp: float = 1.2, min_dist: float = 100, param1: float = 100, param2: float = 30, min_r: int = 40, max_r: int = 200) -> Optional[Tuple[int, int, int]]:
    """Detect dominant circle via HoughCircles. Returns (cx, cy, r) or None."""
    if not _HAS_CV2:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    gray = cv2.medianBlur(gray, 5)
    gray = cv2.GaussianBlur(gray, (9, 9), 2)
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=dp, minDist=min_dist, param1=param1, param2=param2, minRadius=min_r, maxRadius=max_r)
    if circles is None:
        return None
    circles = np.round(circles[0, :]).astype(int)
    # pick largest / most central circle
    h, w = image.shape[:2]
    center = np.array([w / 2, h / 2])
    best = None
    best_score = -1
    for (x, y, r) in circles:
        # score: large radius + near center
        dist = np.linalg.norm(np.array([x, y]) - center)
        score = r - dist * 0.5
        if score > best_score:
            best_score = score
            best = (int(x), int(y), int(r))
    return best


def detect_needle_angle(image: np.ndarray, center: Tuple[int, int], radius: int) -> Optional[float]:
    """Detect needle line through center via HoughLinesP + angular scoring.

    Returns angle in degrees (0 = +x axis, CCW positive, matching math convention).
    For gauge: we convert to gauge polar where 0 is at 12 o'clock optionally handled by GaugeCalibration.
    """
    if not _HAS_CV2:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    # mask to gauge interior
    mask = np.zeros_like(gray)
    cv2.circle(mask, center, int(radius * 0.95), 255, -1)
    masked = cv2.bitwise_and(gray, gray, mask=mask)
    # enhance needle (usually dark) — adaptive threshold + Canny
    blurred = cv2.GaussianBlur(masked, (5, 5), 0)
    # Use Canny with aperture tuned for thin needle
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
    # Mask edges to interior again (remove rim)
    inner_mask = np.zeros_like(gray)
    cv2.circle(inner_mask, center, int(radius * 0.88), 255, -1)
    cv2.circle(inner_mask, center, int(radius * 0.15), 0, -1)  # remove hub
    edges = cv2.bitwise_and(edges, edges, mask=inner_mask)

    # HoughLinesP
    lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi / 180, threshold=30, minLineLength=int(radius * 0.4), maxLineGap=10)
    if lines is None or len(lines) == 0:
        # fallback: use probabilistic Hough with lower threshold
        lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi / 180, threshold=20, minLineLength=int(radius * 0.3), maxLineGap=8)
        if lines is None:
            return None

    # Score lines by distance to center and length
    cx, cy = center
    best_angle: Optional[float] = None
    best_score = -1
    for line in lines:
        # OpenCV 4 returns shape (N,1,4); OpenCV 5 may return (N,4) — normalize
        try:
            if isinstance(line, np.ndarray) and line.shape == (4,):
                x1, y1, x2, y2 = line.tolist()  # type: ignore
            elif isinstance(line, np.ndarray) and line.ndim == 2 and line.shape[1] == 4:
                x1, y1, x2, y2 = line[0].tolist()  # type: ignore
            else:
                # generic fallback: flatten
                flat = np.array(line).flatten().tolist()
                if len(flat) < 4:
                    continue
                x1, y1, x2, y2 = flat[0], flat[1], flat[2], flat[3]
        except Exception:
            continue
        length = math.hypot(x2 - x1, y2 - y1)
        # distance from center to line (point-line distance)
        # line through (x1,y1)-(x2,y2), distance to (cx,cy)
        denom = math.hypot(y2 - y1, x2 - x1)
        if denom == 0:
            continue
        dist = abs((y2 - y1) * cx - (x2 - x1) * cy + x2 * y1 - y2 * x1) / denom
        if dist > radius * 0.15:
            continue  # needle must pass near center
        # angle of line (use longer direction away from center)
        # pick endpoint farther from center
        d1 = math.hypot(x1 - cx, y1 - cy)
        d2 = math.hypot(x2 - cx, y2 - cy)
        tip_x, tip_y = (x1, y1) if d1 > d2 else (x2, y2)
        angle = math.degrees(math.atan2(-(tip_y - cy), tip_x - cx))  # y inverted (image coords)
        # score
        score = length - dist * 2
        if score > best_score:
            best_score = score
            best_angle = angle

    if best_angle is not None:
        # Normalize to [-180, 180]
        while best_angle > 180:
            best_angle -= 360
        while best_angle < -180:
            best_angle += 360
        return best_angle
    return None


def _fallback_angle_from_contour(image: np.ndarray, center: Tuple[int, int], radius: int) -> Optional[float]:
    """Fallback: find needle as largest contour inside gauge that is elongated."""
    if not _HAS_CV2:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    mask = np.zeros_like(gray)
    cv2.circle(mask, center, int(radius * 0.9), 255, -1)
    cv2.circle(mask, center, int(radius * 0.12), 0, -1)
    masked = cv2.bitwise_and(gray, gray, mask=mask)
    _, thresh = cv2.threshold(masked, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    thresh = cv2.bitwise_and(thresh, thresh, mask=mask)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    # pick most elongated contour near center
    best = None
    best_ecc = -1
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < radius * 2 or area > radius * radius * 0.3:
            continue
        # fit line
        if len(cnt) < 5:
            continue
        (vx, vy, x0, y0) = cv2.fitLine(cnt, cv2.DIST_L2, 0, 0.01, 0.01)  # type: ignore
        angle = math.degrees(math.atan2(-float(vy), float(vx)))  # y inverted
        # eccentricity via minAreaRect aspect
        rect = cv2.minAreaRect(cnt)
        w_, h_ = rect[1]
        if w_ == 0 or h_ == 0:
            continue
        aspect = max(w_, h_) / (min(w_, h_) + 1e-6)
        if aspect < 2.0:
            continue
        if aspect > best_ecc:
            best_ecc = aspect
            best = angle
    return best


def analyze_gauge_image(
    image: np.ndarray,
    calibration: GaugeCalibration,
    src_points: Optional[np.ndarray] = None,
    gauge_params: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[float], float, Optional[float], Dict[str, Any]]:
    """Full pipeline: perspective → circle → needle → value.

    Returns (value, confidence, angle_deg, debug_info).
    """
    if not _HAS_CV2:
        # synthetic without cv2: deterministic pseudo value
        h = abs(hash(image.tobytes()[:64])) % 1000 if image.size else 0
        val = calibration.min_value + (h % 100) / 100.0 * (calibration.max_value - calibration.min_value)
        return val, 0.35, None, {"reason": "opencv not installed — synthetic"}

    gp = gauge_params or {}
    dp = float(gp.get("dp", 1.2))
    min_dist = float(gp.get("min_dist", 80))
    param1 = float(gp.get("param1", 100))
    param2 = float(gp.get("param2", 30))
    r_range = gp.get("radius_range", [40, 200])
    min_r, max_r = int(r_range[0]), int(r_range[1])

    # 1) perspective
    warped, M = perspective_correct(image, src_points=src_points, dst_size=int(gp.get("dst_size", 400)))

    # 2) circle
    circle = detect_circle(warped, dp=dp, min_dist=min_dist, param1=param1, param2=param2, min_r=min_r, max_r=max_r)
    if circle is None:
        # try on original if warped failed
        if warped is not image:
            circle = detect_circle(image, dp=dp, min_dist=min_dist, param1=param1, param2=param2, min_r=min_r, max_r=max_r)
            if circle:
                warped = image
        if circle is None:
            return None, 0.0, None, {"stage": "circle_not_found"}

    cx, cy, r = circle

    # 3) needle angle
    angle = detect_needle_angle(warped, (cx, cy), r)
    if angle is None:
        angle = _fallback_angle_from_contour(warped, (cx, cy), r)
    if angle is None:
        return None, 0.1, None, {"stage": "needle_not_found", "circle": circle}

    # 4) angle → value
    value = calibration.angle_to_value(angle)
    # confidence: based on how well angle sits inside calibration + line score
    span = abs(calibration.max_angle - calibration.min_angle)
    dist_to_edge = min(abs(angle - calibration.min_angle), abs(angle - calibration.max_angle))
    # high confidence if well inside span
    conf = 0.9 if dist_to_edge > span * 0.15 else 0.75
    # degrade if radius very small / angle near edge
    if r < 30:
        conf *= 0.7

    debug = {"circle": circle, "angle": angle, "has_warp": M is not None, "warped_shape": warped.shape[:2]}
    return value, conf, angle, debug


def generate_synthetic_gauge_image(
    value: float,
    calibration: Optional[GaugeCalibration] = None,
    size: int = 400,
    noise: bool = True,
) -> np.ndarray:
    """Generate a synthetic gauge image for tests — white dial, black rim, red needle at value."""
    if calibration is None:
        calibration = GaugeCalibration()
    span_v = calibration.max_value - calibration.min_value
    frac = (value - calibration.min_value) / span_v if span_v != 0 else 0.5
    span_a = calibration.max_angle - calibration.min_angle
    angle = calibration.min_angle + frac * span_a - calibration.angle_offset

    if not _HAS_CV2:
        # return dummy array for hash-based fallback
        arr = np.zeros((size, size, 3), dtype=np.uint8)
        arr[:] = int(255 * frac)
        return arr

    img = np.ones((size, size, 3), dtype=np.uint8) * 255
    cx, cy = size // 2, size // 2
    radius = int(size * 0.42)
    # rim
    cv2.circle(img, (cx, cy), radius, (30, 30, 30), 4)
    cv2.circle(img, (cx, cy), 6, (20, 20, 20), -1)
    # tick marks
    for i in range(11):
        a = calibration.min_angle + i / 10.0 * span_a
        rad = math.radians(a)
        # gauge 0 at top typically — we treat angle as math CCW from +x; rotate so 90 is top
        # For visual: needle angle as math angle → image angle (y down) = -angle
        img_a = -a
        r1 = radius - 8
        r2 = radius - 2
        x1 = int(cx + r1 * math.cos(math.radians(img_a)))
        y1 = int(cy + r1 * math.sin(math.radians(img_a)))
        x2 = int(cx + r2 * math.cos(math.radians(img_a)))
        y2 = int(cy + r2 * math.sin(math.radians(img_a)))
        cv2.line(img, (x1, y1), (x2, y2), (0, 0, 0), 2)
    # needle
    rad = math.radians(-angle)  # image coords
    tip_x = int(cx + (radius * 0.85) * math.cos(rad))
    tip_y = int(cy + (radius * 0.85) * math.sin(rad))
    tail_x = int(cx - 12 * math.cos(rad))
    tail_y = int(cy - 12 * math.sin(rad))
    cv2.line(img, (tail_x, tail_y), (tip_x, tip_y), (0, 0, 255), 3)
    cv2.circle(img, (cx, cy), 8, (0, 0, 255), -1)
    if noise:
        # light gaussian noise
        n = np.random.normal(0, 4, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + n, 0, 255).astype(np.uint8)
        # slight blur to mimic camera
        img = cv2.GaussianBlur(img, (3, 3), 0)
    return img


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------
class CameraAdapter(BaseAdapter):
    """Camera gauge-reader adapter.

    Sources (priority):
      1) params["image_path"] — single image file polled
      2) params["video_path"] / "rtsp_url" — VideoCapture stream
      3) injected frame via `inject_frame()` (tests)
      4) synthetic gauge image (offline fallback)

    Emits one NormalizedReading per poll (metric = tags[0].metric or "gauge_value").
    """

    def __init__(self, config: AdapterConfig) -> None:
        super().__init__(config)
        calib_d = config.params.get("calibration", {})
        self.calibration = GaugeCalibration(
            min_angle=float(calib_d.get("min_angle", -135)),
            max_angle=float(calib_d.get("max_angle", 135)),
            min_value=float(calib_d.get("min_value", 0)),
            max_value=float(calib_d.get("max_value", 100)),
            angle_offset=float(calib_d.get("angle_offset", 0)),
        )
        self._cap: Optional[Any] = None
        self._injected_frame: Optional[np.ndarray] = None
        self._last_value: Optional[float] = None
        self.src_points: Optional[np.ndarray] = None
        sp = config.params.get("src_points")
        if sp:
            self.src_points = np.array(sp, dtype=np.float32)

    async def _on_start(self) -> None:
        if not _HAS_CV2:
            self._status = "degraded"
            self._last_error = "opencv not installed — synthetic mode"
            return
        # open capture if configured
        video = self.config.params.get("video_path") or self.config.params.get("rtsp_url")
        if video:
            try:
                cap = cv2.VideoCapture(video)  # type: ignore
                if cap.isOpened():
                    self._cap = cap
                    self._status = "ok"
                else:
                    self._last_error = f"VideoCapture failed to open {video}"
                    self._status = "degraded"
                    cap.release()
            except Exception as e:
                self._last_error = f"VideoCapture error: {e}"
                self._status = "degraded"

    async def _on_stop(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()  # type: ignore
            except Exception:
                pass
            self._cap = None

    def inject_frame(self, frame: np.ndarray) -> None:
        """Test helper — next poll will use this frame."""
        self._injected_frame = frame

    def _load_frame(self) -> Optional[np.ndarray]:
        # 1) injected
        if self._injected_frame is not None:
            f = self._injected_frame
            self._injected_frame = None  # one-shot unless re-injected
            return f
        # 2) image_path
        img_path = self.config.params.get("image_path")
        if img_path and _HAS_CV2:
            try:
                img = cv2.imread(img_path)  # type: ignore
                if img is not None:
                    return img
                self._last_error = f"imread failed for {img_path}"
            except Exception as e:
                self._last_error = f"imread {img_path}: {e}"
        # 3) capture
        if self._cap is not None:
            try:
                ok, frame = self._cap.read()  # type: ignore
                if ok and frame is not None:
                    return frame
                # loop video
                try:
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # type: ignore
                    ok, frame = self._cap.read()  # type: ignore
                    if ok:
                        return frame
                except Exception:
                    pass
            except Exception as e:
                self._last_error = f"cap read: {e}"
        # 4) synthetic
        return None

    async def _poll_once_impl(self) -> List[NormalizedReading]:
        # load frame in thread (cv2 imread/VideoCapture can block)
        frame: Optional[np.ndarray] = None
        if self._injected_frame is not None:
            frame = self._load_frame()
        else:
            frame = await asyncio.to_thread(self._load_frame)

        metric = self.config.tags[0].metric if self.config.tags else "gauge_value"
        unit = self.config.tags[0].unit if self.config.tags else "unit"
        source_tag = self.config.tags[0].source_tag if self.config.tags else "camera"

        if frame is None:
            # synthetic fallback — still produce a reading so pipeline not starved
            return self._synthetic_reading(metric, unit, source_tag, reason="no frame — synthetic fallback")

        # run pipeline in thread (CPU-heavy)
        gauge_params = self.config.params.get("gauge", {})
        calibration = self.calibration

        def _analyze():
            return analyze_gauge_image(frame, calibration, src_points=self.src_points, gauge_params=gauge_params)

        try:
            value, confidence, angle, debug = await asyncio.to_thread(_analyze)
        except Exception as e:
            self._last_error = f"gauge analysis failed: {e}"
            return self._synthetic_reading(metric, unit, source_tag, reason=str(e))

        if value is None:
            self._error_count += 1
            self._last_error = f"gauge detection failed: {debug}"
            # return uncertain synthetic but mark degraded
            self._status = "degraded"
            return self._synthetic_reading(metric, unit, source_tag, reason="detection failed — synthetic fallback")

        # apply tag scale/offset if tag has them
        if self.config.tags:
            tm = self.config.tags[0]
            # gauge value already in calibrated units; still apply scale/offset
            try:
                value = value * tm.scale + tm.offset
            except Exception:
                pass

        # quality from confidence
        quality = Quality.GOOD if confidence >= 0.7 else (Quality.UNCERTAIN if confidence >= 0.4 else Quality.BAD)
        self._last_value = value
        self._last_ok_ts = time.time()
        self._status = "ok"
        # Purposely drop raw frame — DefectEvent/NormalizedReading carry only derived value

        reading = NormalizedReading(
            station_id=self.config.station_id,
            metric=metric,
            value=float(value),
            unit=unit,
            timestamp=time.time(),
            quality=quality,
            protocol=self.protocol,
            adapter_id=self.adapter_id,
            source_tag=source_tag,
            raw_value=None,
        )
        return [reading]

    def _synthetic_reading(self, metric: str, unit: str, source_tag: str, reason: str = "") -> List[NormalizedReading]:
        import math, random

        # deterministic-ish synthetic that still varies
        t = time.time()
        # drift around 50 with sine
        base = 50.0 + 10 * math.sin(t / 20.0) + random.uniform(-1, 1)
        # clamp to calibration
        base = max(self.calibration.min_value, min(self.calibration.max_value, base))
        if self.config.tags:
            tm = self.config.tags[0]
            base = base * tm.scale + tm.offset
        return [
            NormalizedReading(
                station_id=self.config.station_id,
                metric=metric,
                value=float(base),
                unit=unit,
                timestamp=time.time(),
                quality=Quality.UNCERTAIN,
                protocol=self.protocol,
                adapter_id=self.adapter_id,
                source_tag=source_tag,
                raw_value=None,
            )
        ]
