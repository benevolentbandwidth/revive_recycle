from openai import OpenAI
from src.detect import detect_and_crop
from src.identify import identify_brand_model


def run_pipeline(image_path: str) -> list[dict]:
    print(f"[Stage 1] Running YOLO on: {image_path}")
    detections = detect_and_crop(image_path)

    if not detections:
        print("  No phones or laptops detected.")
        return []

    print(f"  Found {len(detections)} device(s).\n")

    client = OpenAI()
    results = []
    total_cost = 0.0

    for i, det in enumerate(detections):
        print(
            f"[Stage 2] Identifying device {i + 1}: {det['label']} "
            f"({det['confidence'] * 100:.1f}% YOLO confidence)"
        )

        brand_info, call_cost = identify_brand_model(det["cropped_path"], det["label"], client)
        total_cost += call_cost
        combined = {**det, **brand_info}
        results.append(combined)

        print(f"  Brand : {brand_info.get('brand', 'unknown')}")
        print(f"  Model : {brand_info.get('model', 'unknown')}")
        print(f"  ID confidence: {brand_info.get('confidence', 'unknown')}")
        print(f"  API cost: ${call_cost:.6f}\n")

    print(f"Total run cost: ${total_cost:.6f}")
    return results
