"""Рендер GLB у прозорі PNG, щоб Flet поставив горщики на полицю."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "3d-models"
OUT = ROOT / "assets" / "models"
WIDTH = 520
HEIGHT = 680

_DTYPE = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}
_SIZE = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def _glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    json_len = struct.unpack_from("<I", data, 12)[0]
    document = json.loads(data[20 : 20 + json_len])
    bin_len = struct.unpack_from("<I", data, 20 + json_len)[0]
    blob = data[28 + json_len : 28 + json_len + bin_len]
    return document, blob


def _accessor(document: dict, blob: bytes, index: int) -> np.ndarray:
    accessor = document["accessors"][index]
    view = document["bufferViews"][accessor["bufferView"]]
    components = _COUNT[accessor["type"]]
    dtype = _DTYPE[accessor["componentType"]]
    width = _SIZE[accessor["componentType"]]
    count = accessor["count"]
    stride = view.get("byteStride", width * components)
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    if stride == width * components:
        raw = blob[start : start + count * stride]
        array = np.frombuffer(raw, dtype=dtype).reshape(count, components)
    else:
        array = np.empty((count, components), dtype=dtype)
        for row in range(count):
            offset = start + row * stride
            array[row] = np.frombuffer(blob[offset : offset + width * components], dtype=dtype)
    return np.array(array, dtype=np.float32)


def _triangles(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    document, blob = _glb(path)
    positions: list[np.ndarray] = []
    colors: list[np.ndarray] = []
    normals: list[np.ndarray] = []
    for primitive in document["meshes"][0]["primitives"]:
        position = _accessor(document, blob, primitive["attributes"]["POSITION"])
        normal = _accessor(document, blob, primitive["attributes"]["NORMAL"])
        if "COLOR_0" in primitive["attributes"]:
            color = _accessor(document, blob, primitive["attributes"]["COLOR_0"])[:, :3]
        else:
            factor = document["materials"][primitive["material"]]["pbrMetallicRoughness"].get(
                "baseColorFactor", [0.7, 0.7, 0.7, 1]
            )
            color = np.tile(np.array(factor[:3], dtype=np.float32), (len(position), 1))
        if "indices" in primitive:
            index = _accessor(document, blob, primitive["indices"]).reshape(-1).astype(np.int64)
        else:
            index = np.arange(len(position), dtype=np.int64)
        face = index.reshape(-1, 3)
        positions.append(position[face])
        colors.append(np.clip(color[face], 0, 1))
        normals.append(normal[face])
    return np.concatenate(positions), np.concatenate(colors), np.concatenate(normals)


def _rotation() -> np.ndarray:
    # Майже фронтальний ракурс: легкий поворот до камери без завалювання горщика.
    yaw, pitch = np.deg2rad(12), np.deg2rad(-10)
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    rotate_y = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float32)
    rotate_x = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]], dtype=np.float32)
    return rotate_x @ rotate_y


def render(
    path: Path,
    destination: Path,
    *,
    width: int = WIDTH,
    height: int = HEIGHT,
    fit: str = "pot",
) -> None:
    points, colors, normals = _triangles(path)
    rotation = _rotation()
    points = points @ rotation.T
    normals = normals @ rotation.T
    light = np.array([0.25, 0.82, 0.52], dtype=np.float32)
    light /= np.linalg.norm(light)
    shade = np.clip((normals * light).sum(axis=2), 0, 1)
    lit = np.clip(colors * (0.38 + 0.62 * shade[..., None]), 0, 1)

    flat = points.reshape(-1, 3)
    if fit == "table":
        model_width = max(float(np.ptp(flat[:, 0])), 0.2)
        model_height = max(float(np.ptp(flat[:, 1])), 0.2)
        span = min(0.90 * width / model_width, 0.78 * height / model_height)
        center_x = float((flat[:, 0].min() + flat[:, 0].max()) / 2)
    else:
        low = points[:, :, 1] < np.percentile(flat[:, 1], 18)
        pot_half = max(float(np.max(np.abs(points[:, :, 0][low]))), 0.2)
        span = 0.70 * width / (2 * pot_half)
        center_x = 0.0
    screen = np.empty_like(points)
    screen[:, :, 0] = (points[:, :, 0] - center_x) * span + width / 2
    floor = float(points[:, :, 1].min())
    screen[:, :, 1] = height - 28 - (points[:, :, 1] - floor) * span
    depth = points[:, :, 2]

    image = np.zeros((height, width, 4), dtype=np.float32)
    buffer = np.full((height, width), -np.inf, dtype=np.float32)
    area = (screen[:, 1, 0] - screen[:, 0, 0]) * (screen[:, 2, 1] - screen[:, 0, 1]) - (
        screen[:, 2, 0] - screen[:, 0, 0]
    ) * (screen[:, 1, 1] - screen[:, 0, 1])
    order = np.argsort(depth.mean(axis=1))
    for index in order:
        if abs(float(area[index])) <= 0.4:
            continue
        xs = screen[index, :, 0]
        ys = screen[index, :, 1]
        min_x = max(int(np.floor(xs.min())), 0)
        max_x = min(int(np.ceil(xs.max())), width - 1)
        min_y = max(int(np.floor(ys.min())), 0)
        max_y = min(int(np.ceil(ys.max())), height - 1)
        if max_x <= min_x or max_y <= min_y:
            continue
        grid_x, grid_y = np.meshgrid(
            np.arange(min_x, max_x + 1),
            np.arange(min_y, max_y + 1),
        )
        x0, y0 = xs[0], ys[0]
        x1, y1 = xs[1], ys[1]
        x2, y2 = xs[2], ys[2]
        denominator = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denominator) < 1e-4:
            continue
        weight_0 = ((y1 - y2) * (grid_x - x2) + (x2 - x1) * (grid_y - y2)) / denominator
        weight_1 = ((y2 - y0) * (grid_x - x2) + (x0 - x2) * (grid_y - y2)) / denominator
        weight_2 = 1 - weight_0 - weight_1
        inside = (weight_0 >= 0) & (weight_1 >= 0) & (weight_2 >= 0)
        if not inside.any():
            continue
        zed = weight_0 * depth[index, 0] + weight_1 * depth[index, 1] + weight_2 * depth[index, 2]
        closer = inside & (zed > buffer[min_y : max_y + 1, min_x : max_x + 1])
        if not closer.any():
            continue
        buffer[min_y : max_y + 1, min_x : max_x + 1][closer] = zed[closer]
        red = weight_0 * lit[index, 0, 0] + weight_1 * lit[index, 1, 0] + weight_2 * lit[index, 2, 0]
        green = weight_0 * lit[index, 0, 1] + weight_1 * lit[index, 1, 1] + weight_2 * lit[index, 2, 1]
        blue = weight_0 * lit[index, 0, 2] + weight_1 * lit[index, 1, 2] + weight_2 * lit[index, 2, 2]
        patch = image[min_y : max_y + 1, min_x : max_x + 1]
        patch[..., 0][closer] = red[closer]
        patch[..., 1][closer] = green[closer]
        patch[..., 2][closer] = blue[closer]
        patch[..., 3][closer] = 1

    bottom = int(np.clip(np.max(screen[:, :, 1]), 0, height - 1))
    center = width // 2
    shadow_y = np.arange(height)[:, None]
    shadow_x = np.arange(width)[None, :]
    shadow_rx = width * (0.30 if fit == "table" else 78 / WIDTH)
    shadow_ry = height * (0.035 if fit == "table" else 16 / HEIGHT)
    ellipse = ((shadow_x - center) / shadow_rx) ** 2 + (
        (shadow_y - min(bottom - 6, height - 8)) / shadow_ry
    ) ** 2
    shadow = (ellipse <= 1) & (image[..., 3] < 0.5)
    image[..., 3][shadow] = 0.28
    image[..., :3][shadow] = 0.15

    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(image, 0, 1) * 255).astype(np.uint8), "RGBA").save(destination)
    print(destination.name)


def main() -> None:
    for source in sorted(SRC.glob("*.glb")):
        render(source, OUT / f"{source.stem}.png")
    table = ROOT / "greenhouse_table_zero.glb"
    if table.exists():
        render(table, OUT / "greenhouse_table.png", width=1600, height=560, fit="table")


if __name__ == "__main__":
    main()
