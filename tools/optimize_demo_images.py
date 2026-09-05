"""Resize the downloaded demo photography into lightweight, consistent WebP assets."""

from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / ".asset-source"
OUTPUT = ROOT / "static" / "images" / "demo"

SIZES = {
    "hero": (1280, 1120),
    "beshbarmak": (920, 720),
    "qazi": (920, 720),
    "manti": (920, 720),
    "lagman": (920, 720),
    "soup": (920, 720),
    "salad": (920, 720),
    "tea": (920, 720),
    "ayran": (920, 720),
    "baursak": (920, 720),
    "dessert": (920, 720),
}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, size in SIZES.items():
        source = SOURCE / f"{name}.source"
        if not source.exists():
            raise FileNotFoundError(source)
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
            image.save(OUTPUT / f"{name}.webp", "WEBP", quality=80, method=6)
            print(f"{name}.webp: {size[0]}x{size[1]}")


if __name__ == "__main__":
    main()
