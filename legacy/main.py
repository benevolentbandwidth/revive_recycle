import sys
from pathlib import Path
from dotenv import load_dotenv
from src.pipeline import run_pipeline

load_dotenv()

if __name__ == "__main__":
    default = Path("images") / "output.jpg"
    image_path = sys.argv[1] if len(sys.argv) > 1 else str(default)
    run_pipeline(image_path)
