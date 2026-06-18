"""Build branding PNG/ICO assets from the master icon artwork."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRANDING = ROOT / "assets" / "branding"
MASTER = BRANDING / "icon-variant-b-monogram-su.png"
MARK = BRANDING / "app-icon-mark.png"
SQUARE = BRANDING / "app-icon-square.png"
ICO = BRANDING / "app.ico"
ICO_SIZES = (256, 128, 64, 48, 32, 16)


def _is_outer_background(red: int, green: int, blue: int) -> bool:
    return red < 35 and green < 35 and blue < 40


def _content_bbox(image):
    pixels = image.load()
    width, height = image.size
    min_x, min_y = width, height
    max_x, max_y = 0, 0
    for y in range(height):
        for x in range(width):
            red, green, blue, _alpha = pixels[x, y]
            if not _is_outer_background(red, green, blue):
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if max_x < min_x or max_y < min_y:
        raise RuntimeError("icon artwork bbox not found")
    return min_x, min_y, max_x, max_y


def _crop_square(image):
    min_x, min_y, max_x, max_y = _content_bbox(image)
    side = max(max_x - min_x + 1, max_y - min_y + 1)
    center_x = (min_x + max_x) // 2
    center_y = (min_y + max_y) // 2
    left = max(0, center_x - side // 2)
    top = max(0, center_y - side // 2)
    right = min(image.width, left + side)
    bottom = min(image.height, top + side)
    left = max(0, right - side)
    top = max(0, bottom - side)
    return image.crop((left, top, right, bottom))


def _remove_outer_background(image):
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if _is_outer_background(red, green, blue):
                pixels[x, y] = (red, green, blue, 0)
    return image


def main() -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("pip install pillow") from exc

    if not MASTER.is_file():
        raise SystemExit(f"missing master icon: {MASTER}")

    source = Image.open(MASTER).convert("RGBA")
    square = _remove_outer_background(_crop_square(source))
    BRANDING.mkdir(parents=True, exist_ok=True)
    square.save(SQUARE, format="PNG", optimize=True)
    square.save(MARK, format="PNG", optimize=True)

    frames = [
        square.resize((size, size), Image.Resampling.LANCZOS)
        for size in ICO_SIZES
    ]
    frames[0].save(
        ICO,
        format="ICO",
        sizes=[(frame.width, frame.height) for frame in frames],
        append_images=frames[1:],
    )
    print(f"wrote {SQUARE}")
    print(f"wrote {MARK}")
    print(f"wrote {ICO} ({ICO.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
