import time

import cv2
import numpy as np


def make_mask(frame_bgr, lo, hi, lo2=None, hi2=None, blur_ksize=5, morph_ksize=5):
    blur = cv2.GaussianBlur(frame_bgr, (blur_ksize, blur_ksize), 0)
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
    if lo2 is not None:
        mask |= cv2.inRange(hsv, np.array(lo2, np.uint8), np.array(hi2, np.uint8))
    if morph_ksize > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_ksize, morph_ksize))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    return mask


def detect(mask, min_area=300.0, min_circularity=0.6):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    stats = {"n_contours": len(cnts), "n_pass_area": 0, "n_pass_shape": 0}
    best = None
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area:
            continue  # ① 면적 필터: 점 노이즈·작은 배경 조각 제거. 대상이 가장 작게 보일 때보다 작게 잡아야 한다
        stats["n_pass_area"] += 1
        peri = cv2.arcLength(c, True)
        circularity = 4 * np.pi * area / (peri * peri + 1e-9)
        if circularity < min_circularity:
            continue  # ② 형상 필터: 길쭉하거나 너덜너덜한 덩어리 제거. 퍽 측면은 직사각형이고 손에 가려지므로 공 기준(0.6)보다 낮춤
        stats["n_pass_shape"] += 1
        if best is None or area > best[0]:
            best = (area, c, circularity)
    if best is None:
        return None, stats
    M = cv2.moments(best[1])  # ③ 모멘트 중심: 픽셀 평균이라 bbox 중심보다 노이즈에 강함
    cx, cy = M["m10"] / M["m00"], M["m01"] / M["m00"]
    x, y, w, h = cv2.boundingRect(best[1])
    return {"center": (cx, cy), "bbox": (x, y, w, h), "area": float(best[0]),
            "circularity": float(best[2])}, stats


class ColorDetector:

    def __init__(self, cfg):
        self.cfg = dict(cfg)
        self.cx = None
        self.cy = None

    def step(self, frame_bgr):
        c = self.cfg
        t0 = time.perf_counter()
        mask = make_mask(frame_bgr, c["lo"], c["hi"], c.get("lo2"), c.get("hi2"),
                         c.get("blur_ksize", 5), c.get("morph_ksize", 5))
        t1 = time.perf_counter()
        r, stats = detect(mask, c.get("min_area", 300.0), c.get("min_circularity", 0.6))
        t2 = time.perf_counter()

        a = c.get("ema_alpha", 0.3)
        if r is None:
            self.cx = self.cy = None
        else:
            cx, cy = r["center"]
            if self.cx is None:
                self.cx, self.cy = cx, cy
            else:
                self.cx = a * cx + (1 - a) * self.cx
                self.cy = a * cy + (1 - a) * self.cy
            r["cx"], r["cy"] = self.cx, self.cy

        stats["t_mask_ms"] = (t1 - t0) * 1e3
        stats["t_detect_ms"] = (t2 - t1) * 1e3
        return r, mask, stats


def draw_overlay(frame_bgr, r):
    out = frame_bgr.copy()
    if r is not None:
        x, y, w, h = r["bbox"]
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.circle(out, (int(r["center"][0]), int(r["center"][1])), 5, (0, 0, 255), -1)
        cv2.putText(out, f"A={r['area']:.0f} c={r['circularity']:.2f}", (x, max(y - 6, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    else:
        cv2.putText(out, "no detection", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return out
