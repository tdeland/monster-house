#!/usr/bin/env python3
"""
Monster eyes: a webcam watches the sidewalk, and two angry cat eyes follow people.
When someone is being tracked the eyes flush from yellow to red and the pupils narrow.

Install:   pip install opencv-python pygame
Test:      python monster_eyes.py --test      (windowed; eyes follow your mouse,
                                               hold the left button to make them angry)
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
import pygame

# ============================ CONFIG ============================
CAMERA_INDEX = 0
EYE_W, EYE_H = 1280, 720      # resolution of ONE projector
WINDOW_POS = (1920, 0)        # top-left corner of projector 1 on your extended desktop
SWAP_EYES = False             # True if the eyes land in the wrong windows
MIRROR_OUTPUT = False          # True for rear projection (image is viewed from the back)
INVERT_TRACKING = True        # flip to False if the eyes look away from people
DETECT_WIDTH = 480            # frames are shrunk to this width before detection
DETECT_EVERY = 2              # run detection on every Nth frame
IDLE_AFTER = 2.0              # seconds without a person before the eyes wander
EYE_SIZE = 520                # width of each eye in pixels (height is ~0.75x)
CALM_COLOR = (255, 196, 40)   # idle color
ANGRY_COLOR = (255, 60, 15)   # color when someone is being watched
RIM_COLOR = (110, 55, 10)     # dark outline around each eye
SHOW_PREVIEW = False          # camera preview window (works on Windows/Linux)
# ================================================================

PAD = 12


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

def bezier(p0, p1, p2, p3, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n
        m = 1 - t
        x = m**3 * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t**3 * p3[0]
        y = m**3 * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def lens(cx, cy, hw, hh, n=20):
    """Leaf shape: pointed top and bottom, widest in the middle (a slit pupil)."""
    left = [(cx - hw * math.sin(math.pi * i / n), cy - hh + 2 * hh * i / n) for i in range(n + 1)]
    right = [(cx + hw * math.sin(math.pi * i / n), cy - hh + 2 * hh * i / n) for i in range(n, -1, -1)]
    return left + right


class EyeAssets:
    """Everything about one eye that never changes: shape, mask, speckled textures."""

    def __init__(self, inner_right):
        self.inner_right = inner_right
        self.w = EYE_SIZE
        self.h = int(EYE_SIZE * 0.79)
        w, h = self.w, self.h
        self.size = (w + 2 * PAD, h + 2 * PAD)

        # Almond shape: straight slanted top edge from the high outer corner down to the
        # pointed inner corner, with a rounded curve underneath.
        curve = bezier((0, 0), (-0.02, 0.95), (0.6, 1.15), (1.0, 0.73))
        self.poly = [(PAD + (u if inner_right else 1 - u) * w, PAD + v * h) for u, v in curve]

        self.mask = pygame.Surface(self.size)
        self.mask.fill((0, 0, 0))
        pygame.draw.polygon(self.mask, (255, 255, 255), self.poly)

        rng = random.Random(7)
        specks = [(rng.random(), rng.random(), rng.uniform(3, 9)) for _ in range(45)]
        self.tex = []
        for color in (CALM_COLOR, ANGRY_COLOR):
            s = pygame.Surface(self.size)
            s.fill(color)
            dark = tuple(int(c * 0.82) for c in color)
            for u, v, r in specks:
                pygame.draw.circle(s, dark, (int(PAD + u * w), int(PAD + v * h)), int(r))
            self.tex.append(s)

        home_u = 0.53 if inner_right else 0.47
        self.pupil_home = (PAD + home_u * w, PAD + 0.58 * h)


def draw_eye(surf, a, look, blink, alert):
    """look is (-1..1, -1..1); blink 0 open..1 closed; alert 0 calm..1 angry."""
    w, h = a.w, a.h
    box = pygame.Surface(a.size)
    box.blit(a.tex[0], (0, 0))
    a.tex[1].set_alpha(int(255 * alert))
    box.blit(a.tex[1], (0, 0))

    px = a.pupil_home[0] + look[0] * w * 0.20
    py = a.pupil_home[1] + look[1] * h * 0.10
    hw = w * 0.105 * (1 - 0.35 * alert)      # pupils narrow when angry
    hh = h * 0.26
    pygame.draw.polygon(box, (0, 0, 0), lens(px, py, hw, hh))
    off = -hw * 0.25 if a.inner_right else hw * 0.25
    pygame.draw.polygon(box, (255, 255, 255), lens(px + off, py, hw * 0.22, hh * 0.68))

    box.blit(a.mask, (0, 0), special_flags=pygame.BLEND_MULT)   # clip everything to the eye shape
    pygame.draw.polygon(box, RIM_COLOR, a.poly, 7)

    surf.fill((0, 0, 0))
    x = EYE_W // 2 - a.size[0] // 2
    y = EYE_H // 2 - a.size[1] // 2
    surf.blit(box, (x, y))

    # blink: two black lids closing toward the middle of the eye
    top_y = y + PAD
    mid_y = top_y + 0.45 * h
    bot_y = top_y + 0.94 * h
    top_edge = top_y + (mid_y - top_y) * blink
    bot_edge = bot_y - (bot_y - mid_y) * blink
    pygame.draw.rect(surf, (0, 0, 0), (0, 0, EYE_W, top_edge))
    pygame.draw.rect(surf, (0, 0, 0), (0, bot_edge, EYE_W, EYE_H - bot_edge))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="windowed test mode, mouse controls the eyes")
    args = ap.parse_args()

    shared = Shared()
    if not args.test:
        threading.Thread(target=tracker_mouse, args=(shared,), daemon=True).start()
        os.environ["SDL_VIDEO_WINDOW_POS"] = "%d,%d" % WINDOW_POS

    pygame.init()
    if args.test:
        screen = pygame.display.set_mode((EYE_W * 2, EYE_H), pygame.SCALED | pygame.RESIZABLE)
    else:
        screen = pygame.display.set_mode((EYE_W * 2, EYE_H), pygame.NOFRAME)
        pygame.mouse.set_visible(False)

    left_assets = EyeAssets(inner_right=True)     # window on the viewer's left
    right_assets = EyeAssets(inner_right=False)   # window on the viewer's right
    eyes = [pygame.Surface((EYE_W, EYE_H)) for _ in range(2)]
    clock = pygame.time.Clock()

    look = [0.0, 0.0]
    alert = 0.0
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
            alert_target = 1.0 if pygame.mouse.get_pressed()[0] else 0.0
        else:
            with shared.lock:
                x, y, seen = shared.x, shared.y, shared.seen
            if now - seen < IDLE_AFTER:
                target = (-x if INVERT_TRACKING else x, y)
                alert_target = 1.0
            else:  # nobody around: wander lazily
                target = (0.6 * math.sin(now * 0.4 + phase), 0.2 * math.sin(now * 0.27 + phase * 2))
                alert_target = 0.0

        k = min(1.0, dt * 7)  # easing so the eyes glide instead of snapping
        look[0] += (target[0] - look[0]) * k
        look[1] += (target[1] - look[1]) * k
        alert += (alert_target - alert) * min(1.0, dt * 4)

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

        draw_eye(eyes[0], left_assets, look, blink, alert)
        draw_eye(eyes[1], right_assets, look, blink, alert)

        out = [pygame.transform.flip(e, True, False) for e in eyes] if MIRROR_OUTPUT else list(eyes)
        if SWAP_EYES:
            out.reverse()
        screen.blit(out[0], (0, 0))
        screen.blit(out[1], (EYE_W, 0))
        pygame.display.flip()


if __name__ == "__main__":
    main()