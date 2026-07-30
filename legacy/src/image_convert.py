from pathlib import Path
from PIL import Image


def convert_to_jpg(input_path: str, output_path: str | None = None) -> str:
    src = Path(input_path)
    dest = Path(output_path) if output_path else src.with_suffix(".jpg")
    Image.open(src).convert("RGB").save(dest, "JPEG")
    return str(dest)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.image_convert <input_path> [output_path]")
        sys.exit(1)
    out = convert_to_jpg(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"Saved: {out}")
