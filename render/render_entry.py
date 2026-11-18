#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_entry.py -- BUILD-TIME renderer for the news-image-20261117 entry.

    python render/render_entry.py render/news_verified.json entry.png

This script is build tooling only: it needs Pillow and Windows' bundled fonts.
The graded runtime is main.ts at the repository root, which copies the
committed entry.png and needs no Pillow, no fonts and no network.

Design notes
------------
* Everything is laid out in a 1024x1024 design space and drawn at SCALE x,
  then downsampled with LANCZOS so type stays crisp at 1x.
* Every string drawn is registered together with its bounding box and its
  allowed zone.  validate_layout() then checks, before a byte is written:
    - every box lies inside the canvas (0..1024);
    - every box lies inside the zone it was declared for (a card, the
      masthead band, the footer band) -- this is what keeps the masthead,
      the date block, the card copy and the footer apart;
    - no two registered text boxes overlap by more than OVERLAP_TOL;
    - the footer clears the bottom rule;
    - the day the image names is actually present.
  A violation raises and the build exits non-zero: a broken layout never
  reaches entry.png.
* copy_fit()/fit_wrapped() shrink the type until a line fits its column and
  the block fits its line budget, which is the automatic half of the
  validation/revision loop.

Deterministic: same spec + same fonts => byte-identical PNG.
"""
from __future__ import annotations

import json
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = r"C:\Windows\Fonts"

SIZE = 1024          # design canvas, also the delivered pixel size
SCALE = 3            # supersample factor
M = 37               # side margin (37 + 950 + 37 == 1024)
CW = SIZE - 2 * M    # 950 content width
GAP_H, GAP_V = 16, 16
COLS, ROWS = 3, 2
CARD_W = (CW - (COLS - 1) * GAP_H) // COLS          # 306
GRID_BOTTOM = 964
STRAP_TOP = 158
FOOTER_RULE_Y = 974
FOOTER_TEXT_Y = 981
SAFE_BOTTOM = 1016      # footer text must end above this
OVERLAP_TOL = 1.0       # square design-units of tolerated text/text overlap

# ---------------------------------------------------------------- palette ---
BG_TOP = (7, 12, 22)
BG_BOT = (14, 24, 40)
INK = (244, 247, 252)
MUTED = (154, 170, 194)
GOLD = (232, 179, 74)
GOLD_D = (150, 112, 44)
CARD_BG = (18, 29, 48)
CARD_LINE = (46, 67, 98)
STRAP_BG = (21, 33, 55)
PANEL_EDGE = (58, 84, 124)

F_REG = "arial.ttf"
F_BLD = "arialbd.ttf"
F_SER = "georgiab.ttf"


def fnt(name: str, size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(FONT_DIR, name), max(1, int(round(size * SCALE))))


def hexcol(s: str):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def rect_overlap(a, b):
    """Intersection area of two (x0, y0, x1, y1) boxes."""
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return 0.0 if (w <= 0 or h <= 0) else w * h


# =============================================================== rendering ==
SCENES = {}


def scene(name):
    def deco(fn):
        SCENES[name] = fn
        return fn
    return deco


def _star(d, cx, cy, r, fill, rot=-90):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.44
        a = math.radians(rot + i * 36)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


@scene("bridge")
def sc_bridge(d, W, H, ac):
    sea_y = int(H * 0.58)
    d.rectangle([0, sea_y, W, H], fill=(15, 34, 57))
    d.rectangle([0, sea_y, W, sea_y + max(1, SCALE)], fill=(44, 88, 128))
    # deck
    dy0, dy1 = int(H * 0.44), int(H * 0.44) + max(3, int(H * 0.035))
    d.rectangle([int(W * 0.03), dy0, int(W * 0.97), dy1], fill=(134, 146, 166))
    # piers
    for fx in (0.13, 0.38, 0.85):
        x = int(W * fx)
        w = max(3, int(W * 0.014))
        d.rectangle([x - w, dy1, x + w, sea_y + int(H * 0.07)], fill=(96, 108, 128))
    # blast gap in the deck
    gx0, gx1 = int(W * 0.55), int(W * 0.66)
    d.rectangle([gx0, dy0, gx1, sea_y + 1], fill=(15, 34, 57))
    cx, cy = int((gx0 + gx1) / 2), dy0
    for i in range(11):
        a = math.radians(-180 + i * 18)
        L = (0.10 + 0.055 * ((i * 7) % 3)) * H
        d.line([(cx, cy), (cx + L * math.cos(a), cy + L * math.sin(a))],
               fill=(244, 178, 74) if i % 2 else (226, 118, 54),
               width=max(2, SCALE))
    for r, col in ((0.075, (168, 150, 132)), (0.05, (196, 182, 164)), (0.033, (216, 206, 190))):
        rr = r * H
        d.ellipse([cx - rr + 2, cy - rr - H * 0.16, cx + rr + 2, cy + rr - H * 0.16], fill=col)
    # drones with a dotted track to the strike
    for fx, fy in ((0.22, 0.20), (0.35, 0.27), (0.16, 0.33)):
        px, py = int(W * fx), int(H * fy)
        s = max(2, int(W * 0.012))
        d.line([(px - s, py), (px + s, py)], fill=(226, 232, 240), width=max(2, SCALE))
        d.line([(px, py - s), (px, py + s)], fill=(226, 232, 240), width=max(2, SCALE))
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(244, 200, 120))
    step = int(W * 0.035)
    x = int(W * 0.40)
    y = int(H * 0.31)
    while x < gx0 - step:
        d.line([(x, y), (x + step * 0.5, y)], fill=(150, 162, 184), width=max(1, SCALE))
        x += step
        y += int(step * 0.28)


@scene("flags")
def sc_flags(d, W, H, ac):
    d.rectangle([0, int(H * 0.82), W, H], fill=(11, 19, 32))
    # poles
    for px in (int(W * 0.17), int(W * 0.83)):
        d.line([(px, int(H * 0.10)), (px, int(H * 0.84))], fill=(146, 158, 180),
               width=max(2, int(W * 0.010)))
    # left flag: green / white / red
    lx0, lx1, ly0, ly1 = int(W * 0.18), int(W * 0.40), int(H * 0.12), int(H * 0.44)
    bh = (ly1 - ly0) // 3
    for i, col in enumerate(((0, 128, 82), (240, 240, 240), (202, 40, 48))):
        d.rectangle([lx0, ly0 + i * bh, lx1, ly0 + (i + 1) * bh + 1], fill=col)
    # right flag: red / white / blue
    rx0, rx1 = int(W * 0.60), int(W * 0.82)
    for i, col in enumerate(((178, 34, 52), (240, 240, 240), (60, 59, 110))):
        d.rectangle([rx0, ly0 + i * bh, rx1, ly0 + (i + 1) * bh + 1], fill=col)
    # the crack between them
    mid, top, bot = int(W * 0.50), int(H * 0.14), int(H * 0.66)
    pts = [(mid, top)]
    y = top
    i = 0
    while y < bot:
        y += (bot - top) // 7
        pts.append((mid + (int(W * 0.045) if i % 2 == 0 else -int(W * 0.045)), min(y, bot)))
        i += 1
    d.line(pts, fill=(232, 150, 70), width=max(3, int(W * 0.012)), joint="curve")
    # two arrows walking away from each other
    ay = int(H * 0.60)
    for sign, x0 in ((-1, mid - int(W * 0.07)), (1, mid + int(W * 0.07))):
        x1 = x0 + sign * int(W * 0.12)
        d.line([(x0, ay), (x1, ay)], fill=(214, 222, 234), width=max(2, SCALE))
        d.polygon([(x1, ay), (x1 - sign * int(W * 0.035), ay - int(H * 0.045)),
                   (x1 - sign * int(W * 0.035), ay + int(H * 0.045))], fill=(214, 222, 234))


@scene("chamber")
def sc_chamber(d, W, H, ac):
    cx, cy = int(W * 0.50), int(H * 0.90)
    R = int(min(W * 0.44, H * 0.74))
    inner = int(R * 0.70)
    seats = []
    for rad, n in ((R, 50), (inner, 50)):
        for i in range(n):
            a = math.pi + (i + 0.5) * math.pi / n
            seats.append((rad * math.cos(a), rad * math.sin(a), a))
    seats.sort(key=lambda s: (round(math.degrees(s[2])), -s[0]))
    dr = max(1.5, R * 0.052)
    blue, other = (91, 141, 239), (206, 86, 78)
    filled = 0
    for i, (dx, dy, _) in enumerate(seats):
        # spread the 56 blue seats evenly through both arcs
        want = int(math.floor((i + 1) * 56 / 100)) > int(math.floor(i * 56 / 100))
        col = blue if want else other
        if want:
            filled += 1
        x, y = cx + dx, cy + dy
        d.ellipse([x - dr, y - dr, x + dr, y + dr], fill=col)
    assert filled == 56, f"expected 56 highlighted seats, drew {filled}"
    # chamber wall
    d.arc([cx - int(R * 1.16), cy - int(R * 1.16), cx + int(R * 1.16), cy + int(R * 1.16)],
          180, 360, fill=(64, 90, 128), width=max(2, int(R * 0.05)))
    # rostrum
    d.rectangle([int(W * 0.44), int(H * 0.78), int(W * 0.56), int(H * 0.95)], fill=(54, 74, 108))
    d.rectangle([int(W * 0.42), int(H * 0.755), int(W * 0.58), int(H * 0.79)], fill=(78, 102, 142))
    _star(d, int(W * 0.13), int(H * 0.20), int(min(W, H) * 0.13), GOLD)


@scene("chair")
def sc_chair(d, W, H, ac):
    d.rectangle([0, int(H * 0.84), W, H], fill=(11, 19, 32))
    # hearing-room panelling
    for i in range(4):
        x = int(W * (0.05 + i * 0.24))
        d.rectangle([x, 0, x + int(W * 0.14), int(H * 0.84)], fill=(21, 33, 54))
    # Fed-style seal
    cx, cy = int(W * 0.26), int(H * 0.46)
    r = int(min(W, H) * 0.30)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(196, 154, 64), width=max(3, SCALE))
    d.ellipse([cx - int(r * 0.74), cy - int(r * 0.74), cx + int(r * 0.74), cy + int(r * 0.74)],
              fill=(14, 24, 40), outline=(140, 110, 46), width=max(2, SCALE))
    for i in range(8):
        a = math.radians(i * 45)
        px, py = cx + int(r * 0.46 * math.cos(a)), cy + int(r * 0.46 * math.sin(a))
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(196, 154, 64))
    # the empty chair
    back_x0, back_x1 = int(W * 0.74), int(W * 0.90)
    seat_x0, seat_x1 = int(W * 0.56), back_x1
    d.rectangle([back_x0, int(H * 0.24), back_x1, int(H * 0.62)], fill=(150, 162, 184))
    d.rectangle([back_x0 + max(2, int(W * 0.02)), int(H * 0.28), back_x1 - max(2, int(W * 0.02)),
                 int(H * 0.44)], fill=(24, 36, 58))
    d.rectangle([seat_x0, int(H * 0.60), seat_x1, int(H * 0.68)], fill=(150, 162, 184))
    for lx in (int(W * 0.60), int(W * 0.86)):
        d.rectangle([lx, int(H * 0.68), lx + max(2, int(W * 0.016)), int(H * 0.88)],
                    fill=(150, 162, 184))
    # unmanned microphone
    mx = int(W * 0.53)
    d.line([(mx, int(H * 0.70)), (mx + int(W * 0.03), int(H * 0.55))], fill=(178, 188, 206),
           width=max(2, SCALE))
    d.ellipse([mx + int(W * 0.026), int(H * 0.505), mx + int(W * 0.056), int(H * 0.575)],
              fill=(178, 188, 206))


@scene("racks")
def sc_racks(d, W, H, ac):
    states = [("ok",) * 6, ["ok", "ok", "warn", "ok", "warn", "dim"],
              ["dim", "warn", "dim", "off", "dim", "off"]]
    on = {"ok": (84, 199, 217), "warn": (230, 150, 60), "dim": (58, 78, 106), "off": (34, 46, 66)}
    for k in range(3):
        x0 = int(W * (0.06 + k * 0.31))
        x1 = x0 + int(W * 0.24)
        d.rectangle([x0, int(H * 0.10), x1, int(H * 0.90)], fill=(24, 36, 56),
                    outline=(62, 88, 126), width=max(2, SCALE))
        for j, st in enumerate(states[k]):
            ly = int(H * (0.15 + j * 0.125))
            d.rectangle([x0 + int(W * 0.03), ly, x1 - int(W * 0.03), ly + int(H * 0.075)],
                        fill=(30, 44, 68))
            for m in range(3):
                lx = x0 + int(W * (0.05 + m * 0.055))
                c = on[st]
                d.rectangle([lx, ly + int(H * 0.022), lx + max(2, int(W * 0.028)),
                             ly + int(H * 0.053)], fill=c)
    # patch cables
    for k in (0, 1):
        xa = int(W * (0.06 + k * 0.31)) + int(W * 0.12)
        xb = int(W * (0.06 + (k + 1) * 0.31)) + int(W * 0.12)
        d.arc([xa, int(H * 0.02), xb, int(H * 0.20)], 0, 180, fill=(96, 132, 176),
              width=max(2, SCALE))


@scene("tower")
def sc_tower(d, W, H, ac):
    d.rectangle([0, int(H * 0.78), W, H], fill=(28, 42, 62))
    d.rectangle([0, int(H * 0.78), W, int(H * 0.78) + max(1, SCALE)], fill=(70, 100, 140))
    # runway dashes
    for i in range(9):
        x = int(W * (0.04 + i * 0.105))
        d.rectangle([x, int(H * 0.92), x + int(W * 0.05), int(H * 0.945)], fill=(176, 186, 202))
    # control tower
    tx0, tx1 = int(W * 0.74), int(W * 0.86)
    d.rectangle([tx0, int(H * 0.34), tx1, int(H * 0.80)], fill=(50, 66, 92))
    d.polygon([(tx0 - int(W * 0.03), int(H * 0.34)), (tx1 + int(W * 0.03), int(H * 0.34)),
               (tx1, int(H * 0.20)), (tx0, int(H * 0.20))], fill=(78, 100, 136))
    d.rectangle([int(W * 0.77), int(H * 0.23), int(W * 0.83), int(H * 0.30)], fill=(168, 206, 232))
    d.line([(int(W * 0.80), int(H * 0.20)), (int(W * 0.80), int(H * 0.10))],
           fill=(160, 172, 192), width=max(2, SCALE))
    d.ellipse([int(W * 0.785), int(H * 0.06), int(W * 0.815), int(H * 0.115)], fill=(214, 74, 62))
    # grounded aircraft
    fy = int(H * 0.66)
    d.ellipse([int(W * 0.10), fy - int(H * 0.06), int(W * 0.52), fy + int(H * 0.06)],
              fill=(174, 184, 200))
    d.polygon([(int(W * 0.13), fy - int(H * 0.04)), (int(W * 0.19), fy - int(H * 0.24)),
               (int(W * 0.25), fy - int(H * 0.04))], fill=(146, 158, 178))
    d.polygon([(int(W * 0.24), fy + int(H * 0.01)), (int(W * 0.40), fy + int(H * 0.20)),
               (int(W * 0.34), fy + int(H * 0.02))], fill=(158, 170, 190))
    d.polygon([(int(W * 0.48), fy - int(H * 0.03)), (int(W * 0.54), fy - int(H * 0.09)),
               (int(W * 0.53), fy - int(H * 0.01))], fill=(146, 158, 178))
    d.ellipse([int(W * 0.46), fy - int(H * 0.03), int(W * 0.50), fy + int(H * 0.01)],
              fill=(96, 132, 168))
    # ground-stop bar across the runway
    for i, col in enumerate(((206, 70, 60), (232, 236, 242))):
        y0 = int(H * (0.855 + i * 0.035))
        d.rectangle([int(W * 0.04), y0, int(W * 0.24), y0 + int(H * 0.035)], fill=col)


# ================================================================ canvas ====
class Canvas:
    def __init__(self):
        self.size = SIZE
        self.img = Image.new("RGB", (SIZE * SCALE, SIZE * SCALE), BG_TOP)
        self.d = ImageDraw.Draw(self.img)
        self.marks = []

    # ---- coordinate helpers (design units in, canvas px out) -------------
    @staticmethod
    def P(v):
        return int(round(v * SCALE))

    def tl(self, s, font):
        """text length in design units"""
        return self.d.textlength(s, font=font) / SCALE

    def wrap(self, text, font, maxw):
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if self.tl(t, font) <= maxw:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    # ---- automatic revision ---------------------------------------------
    def fit_wrapped(self, text, name, maxw, maxlines, start, minv):
        """Shrink the type until the block fits width and line budget."""
        size = start
        while size > minv:
            f = fnt(name, size)
            ls = self.wrap(text, f, maxw)
            if len(ls) <= maxlines and all(self.tl(l, f) <= maxw + 0.01 for l in ls):
                return f, ls, size
            size -= 1
        f = fnt(name, minv)
        ls = self.wrap(text, f, maxw)
        if len(ls) > maxlines or any(self.tl(l, f) > maxw + 0.01 for l in ls):
            raise SystemExit(f"LAYOUT: cannot fit {text[:50]!r} into {maxw}u/{maxlines} lines")
        return f, ls, minv

    def line_w(self, text, font, track=0.0):
        """width a tracked line will actually occupy, in design units"""
        w = self.tl(text, font)
        return w + (len(text) - 1) * track if track and len(text) > 1 else w

    def copy_fit(self, text, name, maxw, start, minv=10, track=0.0):
        """Shrink the type until a single (optionally tracked) line fits."""
        size = start
        while size > minv and self.line_w(text, fnt(name, size), track) > maxw:
            size -= 1
        f = fnt(name, size)
        if self.line_w(text, f, track) > maxw + 0.01:
            raise SystemExit(f"LAYOUT: cannot fit one line {text!r} into {maxw}u")
        return f, size

    # ---- drawing + registration -----------------------------------------
    def text(self, x, y, s, font, fill, anchor="la", track=0.0, zone=None, kind="text"):
        if track:
            w = sum(self.d.textlength(c, font=font) + track * SCALE for c in s) / SCALE
            if s:
                w -= track
            ax = x
            if anchor[0] == "r":
                ax = x - w
            elif anchor[0] == "m":
                ax = x - w / 2
            b = self.d.textbbox((self.P(ax), self.P(y)), s, font=font, anchor="la")
            cx = self.P(ax)
            for ch in s:
                self.d.text((cx, self.P(y)), ch, font=font, fill=fill, anchor="la")
                cx += self.d.textlength(ch, font=font) + track * SCALE
            rect = (float(ax), float(b[1] / SCALE), float(ax + w), float(b[3] / SCALE))
        else:
            self.d.text((self.P(x), self.P(y)), s, font=font, fill=fill, anchor=anchor)
            b = self.d.textbbox((self.P(x), self.P(y)), s, font=font, anchor=anchor)
            rect = tuple(float(v) / SCALE for v in b)
        self.marks.append({"kind": kind, "label": s[:70], "rect": rect, "zone": zone})
        return rect

    def rect(self, box, fill=None, outline=None, width=1, radius=None, kind="shape", zone=None):
        a = [self.P(v) for v in box]
        if radius:
            self.d.rounded_rectangle(a, radius=self.P(radius), fill=fill, outline=outline,
                                     width=max(1, self.P(width)))
        else:
            self.d.rectangle(a, fill=fill, outline=outline,
                             width=max(1, self.P(width)) if outline else 0)
        self.marks.append({"kind": kind, "label": "rect", "rect": tuple(box), "zone": zone})
        return tuple(box)

    def paste(self, im, box, mask=None):
        self.img.paste(im, (self.P(box[0]), self.P(box[1])), mask)

    # ---- checks ----------------------------------------------------------
    def validate(self, require):
        errs = []
        text_marks = [m for m in self.marks if m["kind"] == "text"]
        for m in self.marks:
            x0, y0, x1, y1 = m["rect"]
            if x0 < -0.6 or y0 < -0.6 or x1 > SIZE + 0.6 or y1 > SIZE + 0.6:
                errs.append(f"outside canvas: {m['label']!r} {tuple(round(v,1) for v in m['rect'])}")
            z = m["zone"]
            if z:
                if x0 < z[0] - 0.6 or y0 < z[1] - 0.6 or x1 > z[2] + 0.6 or y1 > z[3] + 0.6:
                    errs.append(f"outside zone {tuple(round(v,1) for v in z)}: "
                                f"{m['label']!r} {tuple(round(v,1) for v in m['rect'])}")
        for i in range(len(text_marks)):
            for j in range(i + 1, len(text_marks)):
                a, b = text_marks[i], text_marks[j]
                ov = rect_overlap(a["rect"], b["rect"])
                if ov > OVERLAP_TOL:
                    errs.append(f"text overlap {ov:.1f}u: {a['label']!r} vs {b['label']!r}")
        for m in text_marks:
            if m["rect"][3] > SAFE_BOTTOM:
                errs.append(f"footer/bottom text below {SAFE_BOTTOM}: {m['label']!r}")
        blob = " | ".join(m["label"] for m in text_marks)
        for need in require:
            if need not in blob:
                errs.append(f"required text missing from the image: {need!r}")
        if errs:
            raise SystemExit("LAYOUT VALIDATION FAILED (entry.png not written):\n  - "
                             + "\n  - ".join(errs))
        return text_marks


# ================================================================ scenes ====
def build_scene(name, w, h, ac):
    W, H = int(round(w * SCALE)), int(round(h * SCALE))
    im = Image.new("RGB", (W, H), (14, 24, 40))
    d = ImageDraw.Draw(im)
    SCENES[name](d, W, H, ac)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1],
                                           radius=int(round(8 * SCALE)), fill=255)
    return im, mask


# ================================================================= build ====
def build(spec, out_path):
    c = Canvas()
    d = c.d
    S = c.P

    # ---- background gradient + vignette ---------------------------------
    for y in range(SIZE):
        t = y / (SIZE - 1)
        col = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
        d.line([(0, S(y)), (S(SIZE) - 1, S(y))], fill=col, width=S(1))
    glow = Image.new("RGB", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([S(-140), S(-260), S(1160), S(560)], fill=(26, 46, 78))
    glow = glow.filter(ImageFilter.GaussianBlur(S(70)))
    c.img = ImageChops.screen(c.img, glow)
    c.d = ImageDraw.Draw(c.img)
    d = c.d

    # full-bleed gold rules
    c.rect((0, 0, SIZE, 7), fill=GOLD)
    c.rect((0, 1017, SIZE, SIZE), fill=GOLD)

    # ---- masthead -------------------------------------------------------
    c.text(M, 26, "THE DAY'S WORLD NEWS IN ONE IMAGE", fnt(F_BLD, 13), GOLD,
           track=2.4, zone=(0, 8, SIZE, 48))
    title_rect = c.text(M, 50, "WORLD NEWS", fnt(F_SER, 64), INK, zone=(0, 8, SIZE, 140))
    day_rect = c.text(SIZE - M, 44, spec["day"], fnt(F_BLD, 40), INK, anchor="ra",
                      zone=(0, 8, SIZE, 92))
    date_rect = c.text(SIZE - M, 92, spec["date"], fnt(F_BLD, 30), GOLD, anchor="ra",
                       zone=(0, 8, SIZE, 140))
    c.rect((M, 140, SIZE - M, 141.5), fill=GOLD)
    c.rect((M, 145.5, SIZE - M, 146.5), fill=GOLD_D)

    # ---- day strap ------------------------------------------------------
    strap_w = CW - 62
    f, lines, sz = c.fit_wrapped(spec["strap"], F_BLD, strap_w, 2, 30, 18)
    lead = sz * 1.30
    strap_h = 18 + len(lines) * lead + 16
    strap_box = (M, STRAP_TOP, SIZE - M, STRAP_TOP + strap_h)
    c.rect(strap_box, fill=STRAP_BG, outline=GOLD_D, width=1.5, radius=10)
    c.rect((M + 4, STRAP_TOP + 6, M + 10, STRAP_TOP + strap_h - 6), fill=GOLD)
    ty = STRAP_TOP + 18
    for ln in lines:
        c.text(M + 24, ty, ln, f, INK, zone=(M, STRAP_TOP, SIZE - M, STRAP_TOP + strap_h))
        ty += lead

    # ---- story grid -----------------------------------------------------
    cards = spec["cards"]
    if len(cards) != COLS * ROWS:
        raise SystemExit(f"spec must hold exactly {COLS * ROWS} cards, got {len(cards)}")
    grid_top = int(STRAP_TOP + strap_h + GAP_V)
    row_h = (GRID_BOTTOM - grid_top - (ROWS - 1) * GAP_V) // ROWS
    if row_h < 300:
        raise SystemExit(f"LAYOUT: row height {row_h} too short for readable cards")
    icon_h = row_h - 196
    PAD = 10

    for idx, card in enumerate(cards):
        r, col = divmod(idx, COLS)
        x0 = M + col * (CARD_W + GAP_H)
        y0 = grid_top + r * (row_h + GAP_V)
        zone = (x0, y0, x0 + CARD_W, y0 + row_h - 6)
        ac = hexcol(card["accent"])

        c.rect((x0, y0, x0 + CARD_W, y0 + row_h), fill=CARD_BG, outline=CARD_LINE,
               width=1.5, radius=14)

        # icon panel: tinted rounded backdrop, scene clipped to its rounded mask
        pw, ph = CARD_W - 2 * PAD, icon_h
        panel = (x0 + PAD, y0 + PAD, x0 + PAD + pw, y0 + PAD + ph)
        c.rect(panel, fill=mix(CARD_BG, ac, 0.13), radius=8)
        sim, mask = build_scene(card["scene"], pw, ph, ac)
        c.paste(sim, (panel[0], panel[1]), mask)
        c.rect(panel, outline=mix(ac, CARD_BG, 0.55), width=1.5, radius=8)

        # kicker row: region · beat on the left, source pill on the right
        tag = f"{card['region']} · {card['beat']}"
        tag_f, tag_sz = c.copy_fit(tag, F_BLD, pw - 100, 13, 10, track=1.5)
        tag_y = y0 + PAD + ph + 16
        tag_rect = c.text(x0 + PAD, tag_y, tag, tag_f, ac, track=1.5,
                          zone=(x0, tag_y - 3, x0 + CARD_W, tag_y + 22))
        src = card["source"]
        src_f, src_sz = c.copy_fit(src, F_BLD, 76, 11, 8)
        src_w = c.tl(src, src_f) + 18
        px1 = x0 + CARD_W - PAD
        px0 = px1 - src_w
        c.rect((px0, tag_y - 4, px1, tag_y + 16), fill=mix(CARD_BG, ac, 0.24),
               outline=mix(ac, CARD_BG, 0.5), width=1, radius=9)
        src_rect = c.text((px0 + px1) / 2 - c.tl(src, src_f) / 2, tag_y - 1, src, src_f,
                          INK, zone=(x0, tag_y - 6, x0 + CARD_W, tag_y + 20))

        # headline
        head_y = tag_y + 28
        hz = (x0, head_y - 4, x0 + CARD_W, y0 + row_h - 8)
        hf, hlines, hsz = c.fit_wrapped(card["headline"], F_BLD, CARD_W - 2 * PAD, 4, 21, 15)
        hy = head_y
        for ln in hlines:
            c.text(x0 + PAD, hy, ln, hf, INK, zone=hz)
            hy += hsz * 1.28

        # keep the kicker and the pill from touching
        if rect_overlap(tag_rect, src_rect) > OVERLAP_TOL:
            raise SystemExit("LAYOUT: kicker and source pill collide on card " + str(idx))

    # ---- footer ---------------------------------------------------------
    c.rect((M, FOOTER_RULE_Y, SIZE - M, FOOTER_RULE_Y + 1.5), fill=GOLD_D)
    fz = (0, FOOTER_RULE_Y, SIZE, SAFE_BOTTOM)
    c.text(M, FOOTER_TEXT_Y, "SOURCES · " + spec["footer_sources"], fnt(F_BLD, 14), MUTED,
           track=1.2, zone=fz)
    c.text(SIZE - M, FOOTER_TEXT_Y, f"{spec['day']} · {spec['date']}", fnt(F_BLD, 14), GOLD,
           track=1.2, anchor="ra", zone=fz)

    # ---- validation ------------------------------------------------------
    marks = c.validate(require=[spec["date"], spec["day"]])

    # ---- downsample + save ----------------------------------------------
    out = c.img.resize((SIZE, SIZE), Image.LANCZOS)
    out.save(out_path, "PNG", optimize=True, compress_level=9)
    return out, marks, dict(day=spec["day"], date=spec["date"], rows=row_h,
                            icon_h=icon_h, strap_h=int(strap_h), texts=len(marks))
def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: render_entry.py <spec.json> <out.png>")
    spec_path, out_path = argv[1], argv[2]
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    img, marks, meta = build(spec, out_path)
    import hashlib
    data = open(out_path, "rb").read()
    print(f"rendered {out_path}")
    print(f"  size       : {img.size[0]}x{img.size[1]}  bytes={len(data)}  "
          f"sha256={hashlib.sha256(data).hexdigest()}")
    print(f"  layout     : row_h={meta['rows']} icon_h={meta['icon_h']} "
          f"strap_h={meta['strap_h']} registered_text_boxes={meta['texts']}")
    print(f"  day named  : {meta['day']} {meta['date']}")
    worst = sorted(marks, key=lambda m: -(m["rect"][2] - m["rect"][0]))[:3]
    for m in worst:
        b = tuple(round(v, 1) for v in m["rect"])
        print(f"  widest text: {m['label'][:46]!r} box={b}")
    print("  checks     : canvas bounds OK, zone bounds OK, no text overlap, "
          f"footer above y={SAFE_BOTTOM}, required date present")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
