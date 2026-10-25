from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "app/lib/core/lumenis_botanical.dart"
BACKGROUND = "#101A16"
STEM = "#B5DA91"
PETAL = "#EEF3DB"
POLLEN = "#BD9750"


def identity_pixels() -> dict[tuple[int, int], str]:
    source = SOURCE.read_text(encoding="utf-8")
    branch = source.split("case LumenisPlant.gypsophila:", 1)[1].split(
        "case LumenisPlant.orchid:", 1
    )[0]
    branches = re.findall(r"\((\d+), (\d+), (\d+), (\d+)\)", branch)
    if not branches:
        raise ValueError("Gypsophila geometry is missing from the app source")
    pixels: dict[tuple[int, int], str] = {}

    def line(x: int, y: int, end_x: int, end_y: int) -> None:
        dx, dy = abs(end_x - x), -abs(end_y - y)
        sx, sy = (1 if x < end_x else -1), (1 if y < end_y else -1)
        error = dx + dy
        while True:
            pixels[x, y] = STEM
            if (x, y) == (end_x, end_y):
                return
            twice = error * 2
            if twice >= dy:
                error += dy
                x += sx
            if twice <= dx:
                error += dx
                y += sy

    for values in branches:
        x, y, ax, ay = map(int, values)
        line(16, 29, ax, ay)
        line(ax, ay, x, y)
        for px, py in ((x - 1, y - 1), (x, y - 1), (x - 1, y), (x, y),
                       (x + 1, y - 1), (x + 1, y)):
            pixels[px, py] = STEM
        for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            pixels[point] = PETAL
        pixels[x, y] = POLLEN
    return pixels


def render(pixels: dict[tuple[int, int], str], size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), BACKGROUND)
    draw = ImageDraw.Draw(image)
    scale = size / 48
    for (x, y), color in pixels.items():
        left, top = round((x + 8) * scale), round((y + 8) * scale)
        right, bottom = round((x + 9) * scale), round((y + 9) * scale)
        if right > left and bottom > top:
            draw.rectangle((left, top, right - 1, bottom - 1), fill=color)
    return image


def main() -> None:
    pixels = identity_pixels()
    rectangles = "\n".join(
        f'  <rect x="{x + 8}" y="{y + 8}" width="1" height="1" fill="{color}"/>'
        for (x, y), color in pixels.items()
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" '
        'shape-rendering="crispEdges">\n'
        f'  <rect width="48" height="48" fill="{BACKGROUND}"/>\n'
        f"{rectangles}\n</svg>\n"
    )
    for target in ("app/web/favicon.svg", "website/public/favicon.svg"):
        (ROOT / target).write_text(svg, encoding="utf-8", newline="\n")
    icons = ROOT / "app/web/icons"
    icons.mkdir(exist_ok=True)
    for size in (192, 512):
        render(pixels, size).save(icons / f"Icon-{size}.png")
    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [render(pixels, size) for size in sizes]
    images[-1].save(
        ROOT / "app/windows/runner/resources/app_icon.ico",
        format="ICO",
        sizes=[(size, size) for size in sizes],
        append_images=images[:-1],
    )
    print("Generated Web, Website and Windows icons from the app Gypsophila geometry.")


if __name__ == "__main__":
    main()
