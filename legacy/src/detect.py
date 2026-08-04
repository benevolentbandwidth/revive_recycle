from PIL import Image
from ultralytics import YOLO

DEVICE_CLASSES = {
    "cell phone": "phone",
    "laptop": "laptop",
}


def detect_and_crop(image_path: str) -> list[dict]:
    model = YOLO("yolov8n.pt")
    results = model(image_path, verbose=False)

    detections = []
    source_img = Image.open(image_path).convert("RGB")

    for result in results:
        for i, box in enumerate(result.boxes):
            class_name = model.names[int(box.cls)]
            if class_name not in DEVICE_CLASSES:
                continue

            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            cropped = source_img.crop((x1, y1, x2, y2))

            crop_path = f"/tmp/device_crop_{i}.jpg"
            cropped.save(crop_path, "JPEG")

            detections.append({
                "label": DEVICE_CLASSES[class_name],
                "confidence": round(float(box.conf), 3),
                "bounding_box": [x1, y1, x2, y2],
                "cropped_path": crop_path,
            })

    return detections
