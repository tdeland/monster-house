from pathlib import Path
from ultralytics import YOLO

MODEL_PATH = Path(__file__).parent / "models" / "yolov8n.pt"
PERSON_CLASS = 0  # COCO class index for "person"

class PersonDetector:
    def __init__(self, confidence_threshold=0.35, image_size=960):
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Weights are downloaded on first run if missing
        self.model = YOLO(str(MODEL_PATH))
        self.confidence_threshold = confidence_threshold
        self.image_size = image_size

    def detect(self, frame):
        results = self.model.predict(
            frame,
            classes=[PERSON_CLASS],
            conf=self.confidence_threshold,
            imgsz=self.image_size,
            verbose=False
        )
        boxes = []
        for left, top, right, bottom in results[0].boxes.xyxy.cpu().numpy():
            boxes.append((int(left), int(top), int(right - left), int(bottom - top)))
        return boxes