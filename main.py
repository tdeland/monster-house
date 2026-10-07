#!/usr/bin/env python3
"""
Monster eyes: a webcam watches the sidewalk, and two glowing eyes follow people.

Install:   pip install opencv-python pygame numpy
Test:      python monster_eyes.py --test      (windowed, eyes follow your mouse)
Run live:  python monster_eyes.py             (borderless window across both projectors)

Setup: set the two projectors up as an extended desktop, side by side. The
window spans both, left half to one projector and right half to the other.
"""
import argparse
import math
import os
import random
import threading
import time

import cv2
import numpy as np
import pygame

# ============================ CONFIG ============================
CAMERA_INDEX = 0
EYE_W, EYE_H = 1280, 720      # resolution of ONE projector
WINDOW_POS = (0, 0)        # top-left corner of projector 1 on your extended desktop
SWAP_EYES = False             # True if the eyes land in the wrong windows
MIRROR_OUTPUT = True          # True for rear projection (image is viewed from the back)
INVERT_TRACKING = True        # flip to False if the eyes look away from people
DETECT_WIDTH = 480            # frames are shrunk to this width before detection
DETECT_EVERY = 2              # run detection on every Nth frame
IDLE_AFTER = 2.0              # seconds without a person before the eyes wander
IRIS_RADIUS = 200             # pixels
IRIS_COLOR = (60,255,60)    # amber; try (60, 255, 60) for green
SHOW_PREVIEW = True          # camera preview window (works on Windows/Linux)
# ================================================================


class Shared:
    def __init__(self):
        self.lock = threading.Lock()
        self.x = 0.0          # -1 (camera left) .. 1 (camera right)
        self.y = 0.0          # -1 (top) .. 1 (bottom)
        self.seen = 0.0       # timestamp of last detection
        self.running = True


def tracker_loop(shared):
    cap = cv2.VideoCapture(CAMERA_INDEX)
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    n = 0
    while shared.running:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.05)
            continue
        n += 1
        if n % DETECT_EVERY:
            continue
        h, w = frame.shape[:2]
        small = cv2.resize(frame, (DETECT_WIDTH, int(h * DETECT_WIDTH / w)))
        sh, sw = small.shape[:2]
        boxes, _ = hog.detectMultiScale(small, winStride=(8, 8), padding=(8, 8), scale=1.05)
        if len(boxes):
            # follow the biggest box (closest person)
            bx, by, bw, bh = max(boxes, key=lambda b: b[2] * b[3])
            x = (bx + bw / 2) / sw * 2 - 1
            y = (by + bh * 0.15) / sh * 2 - 1      # aim at head height
            with shared.lock:
                shared.x, shared.y, shared.seen = x, y, time.time()
            if SHOW_PREVIEW:
                cv2.rectangle(small, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
        if SHOW_PREVIEW:
            cv2.imshow("preview", small)
            cv2.waitKey(1)
    cap.release()


def make_glow(radius, color):
    """Soft-edged glowing disc, brighter toward the rim, darker at the center."""
    size = radius * 2
    yy, xx = np.mgrid[0:size, 0:size]
    d = np.sqrt((xx - radius) ** 2 + (yy - radius) ** 2) / radius
    alpha = np.clip((1 - d) / 0.15, 0, 1)
    shade = 0.55 + 0.45 * np.clip(d, 0, 1)
    rgb = np.zeros((size, size, 3), dtype=np.uint8)
    for i, c in enumerate(color):
        rgb[:, :, i] = (c * shade * alpha).astype(np.uint8)
    return pygame.surfarray.make_surface(rgb.swapaxes(0, 1))


def draw_eye(surf, glow, look, blink, inner_right):
    """Draw one eye as the viewer should see it. look is (-1..1, -1..1); blink 0 open..1 closed."""
    black = (0, 0, 0)
    R = IRIS_RADIUS
    cx, cy = EYE_W // 2, EYE_H // 2
    surf.fill(black)

    ix = cx + look[0] * R * 0.45
    iy = cy + look[1] * R * 0.30
    surf.blit(glow, (ix - R, iy - R))

    # slit pupil, shifted a bit further than the iris for depth
    px = ix + look[0] * R * 0.25
    py = iy + look[1] * R * 0.20
    pygame.draw.ellipse(surf, black, (px - R * 0.12, py - R * 0.8, R * 0.24, R * 1.6))

    # angry brow: a black wedge slanting down toward the inner corner
    s = 1 if inner_right else -1
    x_outer, x_inner = cx - s * R, cx + s * R
    y_outer, y_inner = cy - R * 0.9, cy - R * 0.1
    slope = (y_inner - y_outer) / (x_inner - x_outer)
    y_at = lambda x: y_outer + (x - x_outer) * slope
    pygame.draw.polygon(surf, black, [(0, 0), (EYE_W, 0), (EYE_W, y_at(EYE_W)), (0, y_at(0))])

    # eyelids (also clip the iris to a tidy eye shape)
    top = cy - R * (1 - blink)
    bottom = cy + R * (1 - blink)
    pygame.draw.rect(surf, black, (0, 0, EYE_W, max(top, 0)))
    pygame.draw.rect(surf, black, (0, bottom, EYE_W, EYE_H - bottom))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="windowed test mode, mouse controls the eyes")
    args = ap.parse_args()

    shared = Shared()
    if not args.test:
        threading.Thread(target=tracker_loop, args=(shared,), daemon=True).start()
        os.environ["SDL_VIDEO_WINDOW_POS"] = "%d,%d" % WINDOW_POS

    pygame.init()
    if args.test:
        screen = pygame.display.set_mode((EYE_W * 2, EYE_H), pygame.SCALED | pygame.RESIZABLE)
    else:
        screen = pygame.display.set_mode((EYE_W * 2, EYE_H), pygame.NOFRAME)
        pygame.mouse.set_visible(False)

    glow = make_glow(IRIS_RADIUS, IRIS_COLOR)
    eyes = [pygame.Surface((EYE_W, EYE_H)) for _ in range(2)]
    clock = pygame.time.Clock()

    look = [0.0, 0.0]
    phase = random.random() * 10
    blink_start = None
    next_blink = time.time() + 3

    while True:
        dt = clock.tick(60) / 1000
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_q)):
                shared.running = False
                pygame.quit()
                return

        now = time.time()
        if args.test:
            mx, my = pygame.mouse.get_pos()
            target = (mx / (EYE_W * 2) * 2 - 1, my / EYE_H * 2 - 1)
        else:
            with shared.lock:
                x, y, seen = shared.x, shared.y, shared.seen
            if now - seen < IDLE_AFTER:
                target = (-x if INVERT_TRACKING else x, y)
            else:  # nobody around: wander lazily
                target = (0.6 * math.sin(now * 0.4 + phase), 0.2 * math.sin(now * 0.27 + phase * 2))

        k = min(1.0, dt * 7)  # easing so the eyes glide instead of snapping
        look[0] += (target[0] - look[0]) * k
        look[1] += (target[1] - look[1]) * k

        blink = 0.0
        if blink_start is None and now > next_blink:
            blink_start = now
        if blink_start is not None:
            p = (now - blink_start) / 0.18
            if p >= 1:
                blink_start = None
                next_blink = now + random.uniform(2, 6)
            else:
                blink = 1 - abs(2 * p - 1)

        draw_eye(eyes[0], glow, look, blink, inner_right=True)    # window on the viewer's left
        draw_eye(eyes[1], glow, look, blink, inner_right=False)   # window on the viewer's right

        out = [pygame.transform.flip(e, True, False) for e in eyes] if MIRROR_OUTPUT else eyes
        if SWAP_EYES:
            out.reverse()
        screen.blit(out[0], (0, 0))
        screen.blit(out[1], (EYE_W, 0))
        pygame.display.flip()


if __name__ == "__main__":
    main()