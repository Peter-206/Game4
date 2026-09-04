"""High-resolution multi-format token generator for Pizza Box Party.

Generates high-quality vector-drawn icons for all 13 default tokens at 512x512,
downsampled with high-quality anti-aliasing to 256x256 master images, and exported
as multi-resolution .ico files (16, 24, 32, 48, 64, 128, 256) and .png files.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from PIL import Image, ImageDraw


DEFAULT_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def _draw_pizza(d: ImageDraw.ImageDraw, S: float) -> None:
    # Crust arc
    crust_top = [
        (S * 0.10, S * 0.16), (S * 0.28, S * 0.08), (S * 0.50, S * 0.06),
        (S * 0.72, S * 0.08), (S * 0.90, S * 0.16),
        (S * 0.84, S * 0.26), (S * 0.50, S * 0.18), (S * 0.16, S * 0.26)
    ]
    sauce = [(S * 0.14, S * 0.21), (S * 0.50, S * 0.16), (S * 0.86, S * 0.21), (S * 0.50, S * 0.94)]
    cheese = [(S * 0.16, S * 0.23), (S * 0.50, S * 0.18), (S * 0.84, S * 0.23), (S * 0.50, S * 0.92)]

    # Sauce and cheese base
    d.polygon(sauce, fill=(195, 38, 22, 255))
    d.polygon(cheese, fill=(255, 208, 45, 255))

    # Melted cheese shading and dripping patches
    d.polygon([(S * 0.22, S * 0.26), (S * 0.50, S * 0.21), (S * 0.78, S * 0.26), (S * 0.50, S * 0.82)],
              fill=(255, 228, 75, 255))
    d.polygon([(S * 0.32, S * 0.30), (S * 0.50, S * 0.24), (S * 0.68, S * 0.30), (S * 0.50, S * 0.65)],
              fill=(255, 242, 125, 255))

    # Crust
    d.polygon(crust_top, fill=(222, 150, 48, 255))
    d.line([(S * 0.14, S * 0.16), (S * 0.50, S * 0.08), (S * 0.86, S * 0.16)],
           fill=(252, 195, 95, 255), width=int(S * 0.025))

    # Pepperonis with depth, highlights and spice specks
    peps = [
        (S * 0.50, S * 0.38, S * 0.115),
        (S * 0.33, S * 0.53, S * 0.095),
        (S * 0.66, S * 0.55, S * 0.100),
        (S * 0.49, S * 0.72, S * 0.085),
    ]
    for px, py, pr in peps:
        d.ellipse((px - pr, py - pr, px + pr, py + pr), fill=(188, 32, 26, 255),
                  outline=(130, 20, 16, 255), width=max(1, int(S * 0.015)))
        d.arc((px - pr * 0.72, py - pr * 0.72, px + pr * 0.72, py + pr * 0.72),
              start=200, end=330, fill=(238, 92, 82, 255), width=max(1, int(S * 0.025)))
        d.ellipse((px - pr * 0.25, py - pr * 0.25, px + pr * 0.25, py + pr * 0.25),
                  fill=(145, 22, 18, 255))

    # Herb flakes
    for fx, fy in [
        (S * 0.30, S * 0.34), (S * 0.64, S * 0.36), (S * 0.48, S * 0.53),
        (S * 0.35, S * 0.71), (S * 0.60, S * 0.69), (S * 0.44, S * 0.24)
    ]:
        d.ellipse((fx - S * 0.018, fy - S * 0.012, fx + S * 0.018, fy + S * 0.012),
                  fill=(38, 122, 42, 255))

    # Outlines
    d.line([(S * 0.14, S * 0.22), (S * 0.50, S * 0.94), (S * 0.86, S * 0.22)],
           fill=(65, 30, 12, 255), width=max(2, int(S * 0.035)))
    d.polygon(crust_top, outline=(65, 30, 12, 255), width=max(2, int(S * 0.035)))


def _draw_beer(d: ImageDraw.ImageDraw, S: float) -> None:
    # Mug body
    mug_x1, mug_y1, mug_x2, mug_y2 = S * 0.16, S * 0.28, S * 0.72, S * 0.90
    handle_x1, handle_y1, handle_x2, handle_y2 = S * 0.64, S * 0.38, S * 0.92, S * 0.80

    # Glass handle
    d.rounded_rectangle((handle_x1, handle_y1, handle_x2, handle_y2),
                        radius=int(S * 0.10), fill=(215, 235, 250, 255),
                        outline=(55, 35, 18, 255), width=max(2, int(S * 0.032)))
    d.rounded_rectangle((handle_x1 - S * 0.04, handle_y1 + S * 0.08, handle_x2 - S * 0.09, handle_y2 - S * 0.08),
                        radius=int(S * 0.06), fill=(0, 0, 0, 0))

    # Mug background
    d.rounded_rectangle((mug_x1, mug_y1, mug_x2, mug_y2),
                        radius=int(S * 0.08), fill=(240, 172, 26, 255))

    # Beer golden gradient / ribs
    rib_w = (mug_x2 - mug_x1) / 4
    for i in range(4):
        rx1 = mug_x1 + i * rib_w + S * 0.015
        rx2 = rx1 + rib_w - S * 0.03
        d.rounded_rectangle((rx1, mug_y1 + S * 0.04, rx2, mug_y2 - S * 0.03),
                            radius=int(S * 0.03), fill=(255, 198, 48, 255))

    # Bubbles
    for bx, by, br in [
        (S * 0.26, S * 0.75, S * 0.025), (S * 0.38, S * 0.58, S * 0.030),
        (S * 0.52, S * 0.78, S * 0.022), (S * 0.60, S * 0.50, S * 0.028),
        (S * 0.32, S * 0.42, S * 0.020), (S * 0.48, S * 0.66, S * 0.024)
    ]:
        d.ellipse((bx - br, by - br, bx + br, by + br), fill=(255, 235, 120, 255))

    # Mug Outline
    d.rounded_rectangle((mug_x1, mug_y1, mug_x2, mug_y2),
                        radius=int(S * 0.08), outline=(55, 35, 18, 255), width=max(2, int(S * 0.035)))

    # Foam puffs
    puffs = [
        (S * 0.16, S * 0.28, S * 0.09), (S * 0.28, S * 0.20, S * 0.11),
        (S * 0.44, S * 0.15, S * 0.13), (S * 0.60, S * 0.19, S * 0.11),
        (S * 0.72, S * 0.27, S * 0.09), (S * 0.34, S * 0.26, S * 0.10),
        (S * 0.54, S * 0.25, S * 0.10), (S * 0.13, S * 0.38, S * 0.06), # Drip left
    ]
    # Shadow layer
    for px, py, pr in puffs:
        d.ellipse((px - pr - S * 0.005, py - pr + S * 0.015, px + pr + S * 0.005, py + pr + S * 0.015),
                  fill=(205, 218, 230, 255))
    # Foam white
    for px, py, pr in puffs:
        d.ellipse((px - pr, py - pr, px + pr, py + pr), fill=(255, 255, 255, 255),
                  outline=(55, 35, 18, 255), width=max(1, int(S * 0.022)))


def _draw_dice(d: ImageDraw.ImageDraw, S: float) -> None:
    # 3D isometric or high-contrast rounded die
    box = (S * 0.12, S * 0.12, S * 0.88, S * 0.88)
    radius = int(S * 0.16)

    # Base shadow
    d.rounded_rectangle((box[0], box[1] + S * 0.03, box[2], box[3] + S * 0.03),
                        radius=radius, fill=(195, 202, 212, 255))
    # Die face
    d.rounded_rectangle(box, radius=radius, fill=(252, 252, 254, 255),
                        outline=(40, 42, 48, 255), width=max(2, int(S * 0.038)))

    # Beveled highlight shine
    d.arc((box[0] + S * 0.03, box[1] + S * 0.03, box[2] - S * 0.03, box[3] - S * 0.03),
          start=180, end=270, fill=(255, 255, 255, 255), width=max(1, int(S * 0.03)))

    # Classic 5 pips
    pips = [
        (S * 0.30, S * 0.30),
        (S * 0.70, S * 0.30),
        (S * 0.50, S * 0.50),
        (S * 0.30, S * 0.70),
        (S * 0.70, S * 0.70),
    ]
    pr = S * 0.075
    for px, py in pips:
        # Indented pip shadow
        d.ellipse((px - pr, py - pr + S * 0.008, px + pr, py + pr + S * 0.008), fill=(80, 85, 95, 255))
        d.ellipse((px - pr, py - pr, px + pr, py + pr), fill=(28, 30, 36, 255))
        # Specular glint
        d.ellipse((px - pr * 0.45, py - pr * 0.45, px - pr * 0.1, py - pr * 0.1), fill=(255, 255, 255, 255))


def _draw_cup(d: ImageDraw.ImageDraw, S: float) -> None:
    # Party Solo Cup
    # Tapered trapezoid points
    top_y = S * 0.18
    bot_y = S * 0.88
    tl_x, tr_x = S * 0.22, S * 0.78
    bl_x, br_x = S * 0.30, S * 0.70

    pts = [(tl_x, top_y), (tr_x, top_y), (br_x, bot_y), (bl_x, bot_y)]

    # Cup body
    d.polygon(pts, fill=(215, 32, 32, 255))

    # Highlight sheen on left side
    d.polygon([(tl_x + S * 0.04, top_y), (tl_x + S * 0.14, top_y),
               (bl_x + S * 0.11, bot_y), (bl_x + S * 0.03, bot_y)],
              fill=(245, 88, 88, 255))

    # Horizontal grip ridges
    for ry in [S * 0.38, S * 0.52, S * 0.66]:
        t = (ry - top_y) / (bot_y - top_y)
        lx = tl_x + (bl_x - tl_x) * t
        rx = tr_x + (br_x - tr_x) * t
        d.line([(lx + S * 0.02, ry), (rx - S * 0.02, ry)], fill=(160, 20, 20, 255), width=max(1, int(S * 0.025)))
        d.line([(lx + S * 0.02, ry + S * 0.015), (rx - S * 0.02, ry + S * 0.015)], fill=(250, 95, 95, 255), width=max(1, int(S * 0.018)))

    # Bottom edge curve
    d.ellipse((bl_x, bot_y - S * 0.035, br_x, bot_y + S * 0.035), fill=(175, 22, 22, 255))

    # Cup outline
    d.polygon(pts, outline=(75, 16, 16, 255), width=max(2, int(S * 0.035)))

    # Top rolled rim (white)
    rim_h = S * 0.08
    d.ellipse((tl_x - S * 0.04, top_y - rim_h * 0.6, tr_x + S * 0.04, top_y + rim_h * 0.6),
              fill=(250, 250, 252, 255), outline=(75, 16, 16, 255), width=max(2, int(S * 0.032)))
    # Inner dark cavity
    d.ellipse((tl_x - S * 0.015, top_y - rim_h * 0.35, tr_x + S * 0.015, top_y + rim_h * 0.35),
              fill=(135, 18, 18, 255))


def _draw_star(d: ImageDraw.ImageDraw, S: float) -> None:
    cx, cy = S * 0.50, S * 0.52
    outer_r, inner_r = S * 0.42, S * 0.17
    pts = []
    for i in range(10):
        ang = math.pi / 5 * i - math.pi / 2
        r = outer_r if i % 2 == 0 else inner_r
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))

    # 3D faceted star: draw light and dark triangles from center
    for i in range(10):
        p1 = pts[i]
        p2 = pts[(i + 1) % 10]
        color = (255, 228, 65, 255) if i % 2 == 0 else (218, 155, 18, 255)
        d.polygon([(cx, cy), p1, p2], fill=color)

    # Center sparkle
    d.ellipse((cx - S * 0.06, cy - S * 0.06, cx + S * 0.06, cy + S * 0.06), fill=(255, 255, 180, 255))
    d.polygon(pts, outline=(115, 75, 12, 255), width=max(2, int(S * 0.035)))


def _draw_nerf(d: ImageDraw.ImageDraw, S: float) -> None:
    # Blue foam dart with neon orange suction tip and stabilizer fins
    body_x1, body_y1, body_x2, body_y2 = S * 0.35, S * 0.28, S * 0.65, S * 0.80

    # Fins at base
    d.polygon([(body_x1, body_y2 - S * 0.15), (S * 0.15, body_y2), (body_x1, body_y2)],
              fill=(28, 72, 185, 255), outline=(15, 35, 95, 255), width=max(1, int(S * 0.02)))
    d.polygon([(body_x2, body_y2 - S * 0.15), (S * 0.85, body_y2), (body_x2, body_y2)],
              fill=(28, 72, 185, 255), outline=(15, 35, 95, 255), width=max(1, int(S * 0.02)))

    # Foam cylinder
    d.rounded_rectangle((body_x1, body_y1, body_x2, body_y2),
                        radius=int(S * 0.06), fill=(38, 102, 235, 255))

    # Highlight sheen
    d.rectangle((body_x1 + S * 0.04, body_y1, body_x1 + S * 0.09, body_y2), fill=(85, 150, 255, 255))

    # Foam texture bands
    for fy in [S * 0.44, S * 0.60]:
        d.line([(body_x1, fy), (body_x2, fy)], fill=(25, 68, 168, 255), width=max(1, int(S * 0.018)))

    # Dart body outline
    d.rounded_rectangle((body_x1, body_y1, body_x2, body_y2),
                        radius=int(S * 0.06), outline=(15, 35, 95, 255), width=max(2, int(S * 0.032)))

    # Orange suction tip
    tip_box = (S * 0.28, S * 0.10, S * 0.72, S * 0.32)
    d.ellipse(tip_box, fill=(255, 115, 22, 255), outline=(15, 35, 95, 255), width=max(2, int(S * 0.032)))
    # Suction cup inner ridge
    d.ellipse((S * 0.34, S * 0.14, S * 0.66, S * 0.26), fill=(255, 155, 45, 255))
    d.ellipse((S * 0.40, S * 0.17, S * 0.60, S * 0.23), fill=(215, 78, 12, 255))


def _draw_lion(d: ImageDraw.ImageDraw, S: float) -> None:
    cx, cy = S * 0.50, S * 0.52

    # Fluffy mane
    mane_spikes = 14
    for i in range(mane_spikes):
        ang = math.pi * 2 * i / mane_spikes
        mx = cx + S * 0.36 * math.cos(ang)
        my = cy + S * 0.36 * math.sin(ang)
        d.ellipse((mx - S * 0.13, my - S * 0.13, mx + S * 0.13, my + S * 0.13),
                  fill=(220, 118, 24, 255), outline=(125, 55, 12, 255), width=max(1, int(S * 0.018)))

    # Mane center body
    d.ellipse((cx - S * 0.34, cy - S * 0.34, cx + S * 0.34, cy + S * 0.34),
              fill=(235, 135, 30, 255))

    # Ears
    for ex in [cx - S * 0.23, cx + S * 0.23]:
        d.ellipse((ex - S * 0.09, cy - S * 0.26, ex + S * 0.09, cy - S * 0.08),
                  fill=(255, 215, 65, 255), outline=(125, 55, 12, 255), width=max(1, int(S * 0.02)))
        d.ellipse((ex - S * 0.05, cy - S * 0.22, ex + S * 0.05, cy - S * 0.12),
                  fill=(245, 155, 145, 255))

    # Face circle
    d.ellipse((cx - S * 0.26, cy - S * 0.26, cx + S * 0.26, cy + S * 0.26),
              fill=(255, 218, 68, 255), outline=(125, 55, 12, 255), width=max(2, int(S * 0.032)))

    # Eyes
    for eye_x in [cx - S * 0.10, cx + S * 0.10]:
        d.ellipse((eye_x - S * 0.045, cy - S * 0.08, eye_x + S * 0.045, cy + S * 0.01),
                  fill=(45, 28, 16, 255))
        d.ellipse((eye_x - S * 0.025, cy - S * 0.06, eye_x - S * 0.005, cy - S * 0.03),
                  fill=(255, 255, 255, 255))

    # Snout / muzzle
    d.ellipse((cx - S * 0.12, cy + S * 0.02, cx + S * 0.12, cy + S * 0.17),
              fill=(255, 242, 215, 255), outline=(125, 55, 12, 255), width=max(1, int(S * 0.018)))

    # Nose
    d.polygon([(cx - S * 0.05, cy + S * 0.03), (cx + S * 0.05, cy + S * 0.03), (cx, cy + S * 0.08)],
              fill=(165, 45, 35, 255))

    # Smile lines
    d.arc((cx - S * 0.06, cy + S * 0.07, cx, cy + S * 0.14), start=0, end=180,
          fill=(65, 30, 15, 255), width=max(1, int(S * 0.02)))
    d.arc((cx, cy + S * 0.07, cx + S * 0.06, cy + S * 0.14), start=0, end=180,
          fill=(65, 30, 15, 255), width=max(1, int(S * 0.02)))


def _draw_ducky(d: ImageDraw.ImageDraw, S: float) -> None:
    # Cheerful rubber bath duck
    # Body
    d.ellipse((S * 0.10, S * 0.38, S * 0.85, S * 0.86), fill=(255, 222, 35, 255))
    # Tail upturn
    d.polygon([(S * 0.12, S * 0.52), (S * 0.04, S * 0.40), (S * 0.22, S * 0.44)], fill=(255, 222, 35, 255))

    # Wing
    d.arc((S * 0.22, S * 0.48, S * 0.65, S * 0.74), start=20, end=180,
          fill=(215, 155, 18, 255), width=max(1, int(S * 0.035)))

    # Head
    d.ellipse((S * 0.46, S * 0.14, S * 0.88, S * 0.56), fill=(255, 222, 35, 255))

    # Beak
    d.polygon([(S * 0.76, S * 0.30), (S * 0.96, S * 0.36), (S * 0.76, S * 0.44)],
              fill=(255, 125, 20, 255), outline=(135, 45, 10, 255), width=max(1, int(S * 0.02)))
    d.line([(S * 0.76, S * 0.36), (S * 0.94, S * 0.36)], fill=(135, 45, 10, 255), width=max(1, int(S * 0.015)))

    # Eye
    d.ellipse((S * 0.64, S * 0.24, S * 0.74, S * 0.34), fill=(25, 25, 28, 255))
    d.ellipse((S * 0.67, S * 0.26, S * 0.70, S * 0.29), fill=(255, 255, 255, 255))

    # Outlines
    d.arc((S * 0.10, S * 0.38, S * 0.85, S * 0.86), start=30, end=330,
          fill=(125, 75, 12, 255), width=max(2, int(S * 0.032)))
    d.arc((S * 0.46, S * 0.14, S * 0.88, S * 0.56), start=120, end=40,
          fill=(125, 75, 12, 255), width=max(2, int(S * 0.032)))


def _draw_plane(d: ImageDraw.ImageDraw, S: float) -> None:
    # Modern passenger jet airliner (top view)
    fuselage_x1, fuselage_y1 = S * 0.41, S * 0.08
    fuselage_x2, fuselage_y2 = S * 0.59, S * 0.90

    # Wings
    d.polygon([(S * 0.42, S * 0.40), (S * 0.06, S * 0.62), (S * 0.08, S * 0.72), (S * 0.44, S * 0.58)],
              fill=(225, 232, 245, 255), outline=(35, 55, 95, 255), width=max(2, int(S * 0.025)))
    d.polygon([(S * 0.58, S * 0.40), (S * 0.94, S * 0.62), (S * 0.92, S * 0.72), (S * 0.56, S * 0.58)],
              fill=(225, 232, 245, 255), outline=(35, 55, 95, 255), width=max(2, int(S * 0.025)))

    # Winglet tips
    d.polygon([(S * 0.06, S * 0.62), (S * 0.05, S * 0.54), (S * 0.09, S * 0.63)], fill=(45, 125, 235, 255))
    d.polygon([(S * 0.94, S * 0.62), (S * 0.95, S * 0.54), (S * 0.91, S * 0.63)], fill=(45, 125, 235, 255))

    # Tail stabilizers
    d.polygon([(S * 0.44, S * 0.78), (S * 0.22, S * 0.88), (S * 0.25, S * 0.94), (S * 0.46, S * 0.88)],
              fill=(225, 232, 245, 255), outline=(35, 55, 95, 255), width=max(1, int(S * 0.02)))
    d.polygon([(S * 0.56, S * 0.78), (S * 0.78, S * 0.88), (S * 0.75, S * 0.94), (S * 0.54, S * 0.88)],
              fill=(225, 232, 245, 255), outline=(35, 55, 95, 255), width=max(1, int(S * 0.02)))

    # Fuselage
    d.rounded_rectangle((fuselage_x1, fuselage_y1, fuselage_x2, fuselage_y2),
                        radius=int(S * 0.09), fill=(250, 252, 255, 255),
                        outline=(35, 55, 95, 255), width=max(2, int(S * 0.032)))

    # Blue stripe down center
    d.rounded_rectangle((S * 0.47, S * 0.26, S * 0.53, S * 0.82),
                        radius=int(S * 0.02), fill=(38, 102, 225, 255))

    # Cockpit windshield
    d.rounded_rectangle((S * 0.43, S * 0.15, S * 0.57, S * 0.23),
                        radius=int(S * 0.04), fill=(130, 215, 255, 255),
                        outline=(35, 55, 95, 255), width=max(1, int(S * 0.02)))


def _draw_spoon(d: ImageDraw.ImageDraw, S: float) -> None:
    # Friendly smiling silver spoon
    cx = S * 0.50

    # Handle
    d.rounded_rectangle((cx - S * 0.07, S * 0.44, cx + S * 0.07, S * 0.92),
                        radius=int(S * 0.05), fill=(205, 212, 224, 255),
                        outline=(55, 62, 78, 255), width=max(2, int(S * 0.032)))
    d.rounded_rectangle((cx - S * 0.03, S * 0.48, cx + S * 0.01, S * 0.88),
                        radius=int(S * 0.02), fill=(240, 244, 250, 255))

    # Spoon bowl
    bowl = (S * 0.20, S * 0.08, S * 0.80, S * 0.52)
    d.ellipse(bowl, fill=(225, 230, 240, 255), outline=(55, 62, 78, 255), width=max(2, int(S * 0.036)))

    # Specular rim shine
    d.arc((bowl[0] + S * 0.04, bowl[1] + S * 0.04, bowl[2] - S * 0.04, bowl[3] - S * 0.04),
          start=160, end=270, fill=(255, 255, 255, 255), width=max(1, int(S * 0.03)))

    # Kawaii Face
    # Eyes
    for ex in [cx - S * 0.11, cx + S * 0.11]:
        d.ellipse((ex - S * 0.035, S * 0.24, ex + S * 0.035, S * 0.31), fill=(42, 45, 58, 255))
        d.ellipse((ex - S * 0.02, S * 0.25, ex - S * 0.005, S * 0.27), fill=(255, 255, 255, 255))

    # Rosy blush
    for bx in [cx - S * 0.16, cx + S * 0.16]:
        d.ellipse((bx - S * 0.04, S * 0.31, bx + S * 0.04, S * 0.37), fill=(255, 145, 160, 160))

    # Smile
    d.arc((cx - S * 0.07, S * 0.29, cx + S * 0.07, S * 0.39), start=0, end=180,
          fill=(42, 45, 58, 255), width=max(1, int(S * 0.022)))


def _draw_cactus(d: ImageDraw.ImageDraw, S: float) -> None:
    # Saguaro desert cactus with flower
    # Trunk
    trunk = (S * 0.38, S * 0.18, S * 0.62, S * 0.90)
    d.rounded_rectangle(trunk, radius=int(S * 0.10), fill=(58, 168, 65, 255),
                        outline=(22, 75, 28, 255), width=max(2, int(S * 0.034)))

    # Left branch
    d.polygon([(S * 0.38, S * 0.44), (S * 0.14, S * 0.44), (S * 0.14, S * 0.28),
               (S * 0.26, S * 0.28), (S * 0.26, S * 0.35), (S * 0.38, S * 0.35)],
              fill=(58, 168, 65, 255))
    d.rounded_rectangle((S * 0.14, S * 0.28, S * 0.26, S * 0.52),
                        radius=int(S * 0.05), fill=(58, 168, 65, 255),
                        outline=(22, 75, 28, 255), width=max(2, int(S * 0.032)))
    d.rounded_rectangle((S * 0.14, S * 0.42, S * 0.40, S * 0.52),
                        radius=int(S * 0.05), fill=(58, 168, 65, 255),
                        outline=(22, 75, 28, 255), width=max(2, int(S * 0.032)))

    # Right branch
    d.rounded_rectangle((S * 0.74, S * 0.34, S * 0.86, S * 0.58),
                        radius=int(S * 0.05), fill=(58, 168, 65, 255),
                        outline=(22, 75, 28, 255), width=max(2, int(S * 0.032)))
    d.rounded_rectangle((S * 0.60, S * 0.48, S * 0.86, S * 0.58),
                        radius=int(S * 0.05), fill=(58, 168, 65, 255),
                        outline=(22, 75, 28, 255), width=max(2, int(S * 0.032)))

    # Re-draw trunk outline over branch seams
    d.rounded_rectangle(trunk, radius=int(S * 0.10), fill=(58, 168, 65, 255),
                        outline=(22, 75, 28, 255), width=max(2, int(S * 0.034)))

    # Vertical rib ridges
    d.line([(S * 0.44, S * 0.24), (S * 0.44, S * 0.86)], fill=(38, 125, 45, 255), width=max(1, int(S * 0.02)))
    d.line([(S * 0.50, S * 0.22), (S * 0.50, S * 0.86)], fill=(75, 195, 85, 255), width=max(1, int(S * 0.02)))
    d.line([(S * 0.56, S * 0.24), (S * 0.56, S * 0.86)], fill=(38, 125, 45, 255), width=max(1, int(S * 0.02)))

    # Spines
    for sy in [S * 0.32, S * 0.48, S * 0.64, S * 0.78]:
        d.line([(S * 0.41, sy), (S * 0.34, sy - S * 0.03)], fill=(235, 245, 220, 255), width=max(1, int(S * 0.012)))
        d.line([(S * 0.59, sy), (S * 0.66, sy - S * 0.03)], fill=(235, 245, 220, 255), width=max(1, int(S * 0.012)))

    # Top blooming flower
    flower_cx, flower_cy = S * 0.50, S * 0.16
    for ang_deg in [0, 45, 90, 135, 180, 225, 270, 315]:
        rad = math.radians(ang_deg)
        fx = flower_cx + S * 0.06 * math.cos(rad)
        fy = flower_cy + S * 0.06 * math.sin(rad)
        d.ellipse((fx - S * 0.04, fy - S * 0.04, fx + S * 0.04, fy + S * 0.04), fill=(248, 55, 115, 255))
    d.ellipse((flower_cx - S * 0.045, flower_cy - S * 0.045, flower_cx + S * 0.045, flower_cy + S * 0.045),
              fill=(255, 225, 45, 255))


def _draw_crown(d: ImageDraw.ImageDraw, S: float) -> None:
    # Royal gold crown with gems
    base_box = (S * 0.12, S * 0.62, S * 0.88, S * 0.86)

    # Velvet purple cushion inside
    d.ellipse((S * 0.22, S * 0.35, S * 0.78, S * 0.75), fill=(125, 30, 145, 255))

    # Crown peaks
    peaks = [
        [(S * 0.14, S * 0.64), (S * 0.12, S * 0.28), (S * 0.30, S * 0.50)],
        [(S * 0.30, S * 0.50), (S * 0.50, S * 0.18), (S * 0.70, S * 0.50)],
        [(S * 0.70, S * 0.50), (S * 0.88, S * 0.28), (S * 0.86, S * 0.64)],
    ]
    for poly in peaks:
        d.polygon(poly, fill=(255, 208, 35, 255), outline=(135, 85, 10, 255), width=max(2, int(S * 0.032)))

    # Pearls on top of points
    for px, py in [(S * 0.12, S * 0.28), (S * 0.50, S * 0.18), (S * 0.88, S * 0.28)]:
        d.ellipse((px - S * 0.06, py - S * 0.06, px + S * 0.06, py + S * 0.06),
                  fill=(255, 245, 195, 255), outline=(135, 85, 10, 255), width=max(1, int(S * 0.02)))

    # Base band
    d.rounded_rectangle(base_box, radius=int(S * 0.06), fill=(255, 208, 35, 255),
                        outline=(135, 85, 10, 255), width=max(2, int(S * 0.035)))

    # Embedded Gems
    gem_y = (base_box[1] + base_box[3]) / 2
    gems = [
        (S * 0.26, gem_y, (225, 32, 42, 255)),   # Ruby
        (S * 0.50, gem_y, (32, 95, 235, 255)),   # Sapphire
        (S * 0.74, gem_y, (32, 195, 65, 255)),   # Emerald
    ]
    for gx, gy, gcol in gems:
        gr = S * 0.06
        d.ellipse((gx - gr, gy - gr, gx + gr, gy + gr), fill=gcol, outline=(135, 85, 10, 255), width=max(1, int(S * 0.018)))
        d.ellipse((gx - gr * 0.45, gy - gr * 0.45, gx - gr * 0.1, gy - gr * 0.1), fill=(255, 255, 255, 255))


def _draw_taco(d: ImageDraw.ImageDraw, S: float) -> None:
    # Crispy party taco
    # Shell arc points
    shell_top = [(S * 0.08, S * 0.52), (S * 0.18, S * 0.22), (S * 0.50, S * 0.12), (S * 0.82, S * 0.22), (S * 0.92, S * 0.52)]
    shell_bot = [(S * 0.08, S * 0.52), (S * 0.18, S * 0.82), (S * 0.50, S * 0.90), (S * 0.82, S * 0.82), (S * 0.92, S * 0.52)]

    # Back shell
    d.polygon(shell_top + list(reversed(shell_bot)), fill=(235, 178, 55, 255))

    # Filling (meat layer)
    d.ellipse((S * 0.15, S * 0.32, S * 0.85, S * 0.68), fill=(130, 62, 22, 255))

    # Shredded lettuce (green ribbons)
    for lx in [S * 0.25, S * 0.38, S * 0.52, S * 0.65]:
        d.rounded_rectangle((lx, S * 0.32, lx + S * 0.12, S * 0.56),
                            radius=int(S * 0.03), fill=(65, 185, 55, 255))

    # Cheese strands (yellow)
    for cx in [S * 0.28, S * 0.45, S * 0.60]:
        d.line([(cx, S * 0.34), (cx + S * 0.06, S * 0.52)], fill=(255, 218, 45, 255), width=max(1, int(S * 0.025)))

    # Tomato cubes (red)
    for tx, ty in [(S * 0.32, S * 0.40), (S * 0.50, S * 0.36), (S * 0.68, S * 0.42)]:
        d.rounded_rectangle((tx - S * 0.04, ty - S * 0.04, tx + S * 0.04, ty + S * 0.04),
                            radius=int(S * 0.015), fill=(225, 38, 28, 255))

    # Front shell fold
    front_shell = [(S * 0.08, S * 0.52), (S * 0.18, S * 0.78), (S * 0.50, S * 0.86), (S * 0.82, S * 0.78), (S * 0.92, S * 0.52)]
    d.polygon(front_shell + [(S * 0.50, S * 0.60)], fill=(245, 192, 65, 255),
              outline=(125, 75, 15, 255), width=max(2, int(S * 0.035)))

    # Shell toasted speckles
    for sx, sy in [(S * 0.28, S * 0.72), (S * 0.48, S * 0.78), (S * 0.68, S * 0.74)]:
        d.ellipse((sx - S * 0.02, sy - S * 0.015, sx + S * 0.02, sy + S * 0.015), fill=(185, 125, 30, 255))


TOKEN_DRAWERS = {
    "pizza":  _draw_pizza,
    "beer":   _draw_beer,
    "dice":   _draw_dice,
    "cup":    _draw_cup,
    "star":   _draw_star,
    "nerf":   _draw_nerf,
    "lion":   _draw_lion,
    "ducky":  _draw_ducky,
    "plane":  _draw_plane,
    "spoon":  _draw_spoon,
    "cactus": _draw_cactus,
    "crown":  _draw_crown,
    "taco":   _draw_taco,
}


def render_token_image(name: str, size: int = 256) -> Image.Image:
    """Render a crisp antialiased token image at the specified resolution."""
    drawer = TOKEN_DRAWERS.get(name, _draw_star)
    canvas_size = size * 2
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    drawer(draw, canvas_size)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def generate_all_tokens(output_dir: str | Path,
                        sizes: list[tuple[int, int]] = DEFAULT_SIZES) -> dict[str, tuple[Path, Path]]:
    """Generate multi-resolution .ico and .png files for all 13 default tokens."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated = {}

    for name in TOKEN_DRAWERS:
        master_img = render_token_image(name, size=256)
        ico_path = out / f"{name}.ico"
        png_path = out / f"{name}.png"

        # Save multi-resolution .ico
        master_img.save(ico_path, format="ICO", sizes=sizes)
        # Save high-res master .png
        master_img.save(png_path, format="PNG")

        generated[name] = (ico_path, png_path)

    return generated


if __name__ == "__main__":
    target = Path(__file__).parent / "assets" / "tokens" / "default"
    print(f"Generating default tokens in: {target}")
    results = generate_all_tokens(target)
    print(f"Successfully generated {len(results)} tokens (.ico + .png multi-res).")
