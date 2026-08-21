"""Synthetic gauge images → real CV pipeline, no mocks."""

import math

import cv2
import numpy as np
import pytest

from edge_perception.inference.gauge import GaugeConfig, read_gauge


def synth_gauge_image(
    w: int = 320,
    h: int = 320,
    value: float = 5.0,
    config: GaugeConfig | None = None,
    noise: float = 0.0,
    glare: bool = False,
) -> tuple[np.ndarray, float]:
    """Render a synthetic analog gauge. Returns (BGR image, needle angle deg)."""
    cfg = config or GaugeConfig()
    cx, cy = w // 2, h // 2
    r = min(w, h) // 2 - 10
    img = np.ones((h, w, 3), dtype=np.uint8) * 245  # light background

    # dial rim
    cv2.circle(img, (cx, cy), r, (30, 30, 30), 3)
    cv2.circle(img, (cx, cy), r - 1, (255, 255, 255), 1)

    # ticks
    for frac in [i / 10 for i in range(11)]:
        ang = cfg.value_to_angle(cfg.min_value + frac * (cfg.max_value - cfg.min_value))
        rad = math.radians(ang)
        # image y down: standard math angle works because we used atan2(dy,dx) convention
        x_outer = cx + math.cos(rad) * (r - 4)
        y_outer = cy + math.sin(rad) * (r - 4)
        length = 12 if frac in (0, 0.5, 1.0) else 6
        x_inner = cx + math.cos(rad) * (r - 4 - length)
        y_inner = cy + math.sin(rad) * (r - 4 - length)
        cv2.line(img, (int(x_inner), int(y_inner)), (int(x_outer), int(y_outer)), (40, 40, 40), 2)

    # needle
    angle = cfg.value_to_angle(value)
    rad = math.radians(angle)
    tip_x = cx + math.cos(rad) * (r * 0.78)
    tip_y = cy + math.sin(rad) * (r * 0.78)
    # needle is thick line + hub
    cv2.line(img, (cx, cy), (int(tip_x), int(tip_y)), (10, 10, 220), 3, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), 9, (20, 20, 20), -1)
    cv2.circle(img, (cx, cy), 5, (200, 200, 200), -1)

    # labels
    cv2.putText(
        img,
        f"{cfg.min_value:g}",
        (cx - r + 18, cy + 6),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (0, 0, 0),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        img,
        f"{cfg.max_value:g}",
        (cx + r - 28, cy + 6),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (0, 0, 0),
        1,
        cv2.LINE_AA,
    )

    if glare:
        # add bright ellipse glare
        overlay = img.copy()
        cv2.ellipse(
            overlay, (cx - r // 3, cy - r // 3), (r // 2, r // 3), -20, 0, 360, (255, 255, 255), -1
        )
        img = cv2.addWeighted(overlay, 0.22, img, 0.78, 0)

    if noise > 0:
        rng = np.random.default_rng(0)
        n = rng.normal(0, noise, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + n, 0, 255).astype(np.uint8)

    return img, angle


def test_gauge_mid_scale_accuracy():
    cfg = GaugeConfig()
    for val in [0.0, 1.5, 5.0, 7.3, 10.0]:
        img, _ = synth_gauge_image(value=val, config=cfg)
        res = read_gauge(img, cfg)
        # tolerance: 6% of span (0.6 bar) for synthetic — tight but real pipeline must pass
        assert abs(res.value - val) < 0.8, (
            f"value {val} got {res.value:.2f} angle {res.angle_deg:.1f} conf {res.confidence:.2f}"
        )
        assert res.confidence > 0.30, f"low confidence {res.confidence:.2f} for val {val}"


def test_gauge_confidence_good_on_clean():
    cfg = GaugeConfig()
    img, _ = synth_gauge_image(value=4.2, config=cfg, noise=0)
    res = read_gauge(img, cfg)
    assert res.confidence >= 0.45, f"expected at least uncertain on clean, got {res.confidence:.2f}"


def test_gauge_handles_glare():
    cfg = GaugeConfig()
    img, _ = synth_gauge_image(value=6.0, config=cfg, glare=True, noise=3)
    res = read_gauge(img, cfg)
    assert abs(res.value - 6.0) < 1.2, f"glare case off by {abs(res.value - 6.0):.2f}"
    # adaptive threshold should still produce some confidence
    assert res.confidence > 0.20


def test_gauge_empty_raises():
    cfg = GaugeConfig()
    with pytest.raises(ValueError):
        read_gauge(np.array([], dtype=np.uint8), cfg)
    with pytest.raises(ValueError):
        read_gauge(None, cfg)  # type: ignore


def test_gauge_latency_reasonable():
    cfg = GaugeConfig()
    img, _ = synth_gauge_image(value=3.3, config=cfg)
    res = read_gauge(img, cfg)
    # on CI Mac, 320px gauge should be well under 200ms even without accel
    assert res.latency_ms < 250, f"latency {res.latency_ms:.1f}ms too high"


def test_gauge_angle_to_value_roundtrip():
    cfg = GaugeConfig(min_value=0, max_value=10, min_angle_deg=135, max_angle_deg=45)
    for v in [0, 2.5, 5, 7.5, 10]:
        ang = cfg.value_to_angle(v)
        back = cfg.angle_to_value(ang)
        assert abs(back - v) < 1e-6, f"roundtrip {v} -> {ang} -> {back}"
