"""Рендер горщиків для сцени і меню в однаковому масштабі: assets/pots/*.png.

render_models.py масштабує кожну модель окремо, тому горщики виходять різного розміру,
а високі рослини обрізаються. Тут ширину горщика міряємо за теракотовими вершинами,
тож горщик однаковий на всіх етапах і в усіх культур. Висота кадру спільна для всіх
моделей, щоб не різати верхівки.

Запуск: .venv/bin/python scripts/render_pots.py   (потрібні numpy і Pillow)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_models import SRC, _rotation, _triangles  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "pots"
WIDTH = 400
POT_SHARE = 0.62  # ширина горщика від ширини кадру
BOTTOM_PAD = 24
TOP_PAD = 12
SKIP = {"pot_soil"}


def _pot_half_width(points: np.ndarray, colors: np.ndarray) -> float:
    """Пів ширини горщика за кольором: червоно-коричневі вершини. Запасний шлях — нижня третина."""
    flat_p = points.reshape(-1, 3)
    flat_c = colors.reshape(-1, 3)
    r, g, b = flat_c[:, 0], flat_c[:, 1], flat_c[:, 2]
    terracotta = (r > 0.25) & (r > g * 1.35) & (r > b * 1.35) & (g > b * 0.6)
    if terracotta.sum() < 30:
        low = flat_p[:, 1] < flat_p[:, 1].min() + np.ptp(flat_p[:, 1]) * 0.33
        terracotta = low
    xs = flat_p[terracotta, 0]
    return max(float(np.max(np.abs(xs - np.median(xs)))), 0.05)


def _prepare(path: Path) -> tuple[np.ndarray, np.ndarray, float, float]:
    points, colors, normals = _triangles(path)
    rotation = _rotation()
    points = points @ rotation.T
    normals = normals @ rotation.T
    light = np.array([0.25, 0.82, 0.52], dtype=np.float32)
    light /= np.linalg.norm(light)
    shade = np.clip((normals * light).sum(axis=2), 0, 1)
    lit = np.clip(colors * (0.38 + 0.62 * shade[..., None]), 0, 1)
    half = _pot_half_width(points, colors)
    span = POT_SHARE * WIDTH / (2 * half)
    flat = points.reshape(-1, 3)
    pot_x = float(np.median(flat[:, 0]))
    height_px = float(np.ptp(flat[:, 1])) * span
    return points, lit, span, pot_x, height_px  # type: ignore[return-value]


def _raster(points: np.ndarray, lit: np.ndarray, span: float, center_x: float, height: int) -> np.ndarray:
    screen = np.empty_like(points)
    screen[:, :, 0] = (points[:, :, 0] - center_x) * span + WIDTH / 2
    floor = float(points[:, :, 1].min())
    screen[:, :, 1] = height - BOTTOM_PAD - (points[:, :, 1] - floor) * span
    depth = points[:, :, 2]
    image = np.zeros((height, WIDTH, 4), dtype=np.float32)
    buffer = np.full((height, WIDTH), -np.inf, dtype=np.float32)
    for index in np.argsort(depth.mean(axis=1)):
        xs, ys = screen[index, :, 0], screen[index, :, 1]
        min_x, max_x = max(int(np.floor(xs.min())), 0), min(int(np.ceil(xs.max())), WIDTH - 1)
        min_y, max_y = max(int(np.floor(ys.min())), 0), min(int(np.ceil(ys.max())), height - 1)
        if max_x <= min_x or max_y <= min_y:
            continue
        x0, y0, x1, y1, x2, y2 = xs[0], ys[0], xs[1], ys[1], xs[2], ys[2]
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-4:
            continue
        gx, gy = np.meshgrid(np.arange(min_x, max_x + 1), np.arange(min_y, max_y + 1))
        w0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / den
        w1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        zed = w0 * depth[index, 0] + w1 * depth[index, 1] + w2 * depth[index, 2]
        window = buffer[min_y : max_y + 1, min_x : max_x + 1]
        closer = inside & (zed > window)
        if not closer.any():
            continue
        window[closer] = zed[closer]
        patch = image[min_y : max_y + 1, min_x : max_x + 1]
        for channel in range(3):
            value = w0 * lit[index, 0, channel] + w1 * lit[index, 1, channel] + w2 * lit[index, 2, channel]
            patch[..., channel][closer] = value[closer]
        patch[..., 3][closer] = 1
    # М'яка тінь під горщиком.
    yy, xx = np.arange(height)[:, None], np.arange(WIDTH)[None, :]
    ellipse = ((xx - WIDTH / 2) / (WIDTH * 0.2)) ** 2 + ((yy - (height - BOTTOM_PAD + 2)) / 9) ** 2
    shadow = (ellipse <= 1) & (image[..., 3] < 0.5)
    image[..., 3][shadow] = 0.25
    image[..., :3][shadow] = 0.15
    return image


def main() -> None:
    sources = [path for path in sorted(SRC.glob("*.glb")) if path.stem not in SKIP]
    prepared = {path: _prepare(path) for path in sources}
    height = int(max(item[4] for item in prepared.values()) + BOTTOM_PAD + TOP_PAD)
    OUT.mkdir(parents=True, exist_ok=True)
    for path, (points, lit, span, pot_x, _h) in prepared.items():
        image = _raster(points, lit, span, pot_x, height)
        Image.fromarray((np.clip(image, 0, 1) * 255).astype(np.uint8), "RGBA").save(OUT / f"{path.stem}.png")
    print(f"{len(prepared)} PNG у {OUT.relative_to(ROOT)}, кадр {WIDTH}×{height}, дно на {height - BOTTOM_PAD}")


if __name__ == "__main__":
    main()
