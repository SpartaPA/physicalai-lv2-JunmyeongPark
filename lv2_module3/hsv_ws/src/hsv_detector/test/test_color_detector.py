import cv2
import numpy as np

from hsv_detector.color_detector import ColorDetector, detect, make_mask

BLUE_BGR = (200, 60, 20)
CFG = dict(lo=[100, 120, 40], hi=[125, 255, 255], min_area=300, min_circularity=0.3, ema_alpha=1.0)


def _frame(rect=None):
    f = np.full((360, 640, 3), 128, np.uint8)
    if rect:
        x, y, w, h = rect
        cv2.rectangle(f, (x, y), (x + w, y + h), BLUE_BGR, -1)
    return f


def test_detects_blue_rect_center():
    r, mask, stats = ColorDetector(CFG).step(_frame((300, 150, 40, 60)))
    assert r is not None
    assert abs(r['cx'] - 320) < 2 and abs(r['cy'] - 180) < 2
    assert stats['n_pass_shape'] == 1


def test_no_target_returns_none():
    r, mask, stats = ColorDetector(CFG).step(_frame())
    assert r is None and cv2.countNonZero(mask) == 0


def test_min_area_rejects_small_blob():
    mask = make_mask(_frame((300, 150, 10, 10)), CFG['lo'], CFG['hi'])
    r, stats = detect(mask, min_area=300)
    assert r is None and stats['n_contours'] == 1 and stats['n_pass_area'] == 0


def test_miss_resets_ema():
    d = ColorDetector({**CFG, 'ema_alpha': 0.3})
    d.step(_frame((300, 150, 40, 60)))
    d.step(_frame())
    assert d.cx is None
