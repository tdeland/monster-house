import argparse

import cv2

from camera_config import load_camera_source
from camera_stream import LatestFrameReader

parser = argparse.ArgumentParser(description="Preview the configured camera.")
parser.add_argument(
    "--detect",
    action="store_true",
    help="also load YOLO and draw detected people (requires working PyTorch)",
)
args = parser.parse_args()

detector = None
if args.detect:
    from person_detector import PersonDetector

    detector = PersonDetector()

camera_source = load_camera_source()
reader = LatestFrameReader(camera_source)
print("Camera stream opened:", reader.opened)

while True:
    frame = reader.read(timeout=5)
    if frame is None:
        break
    if detector is not None:
        for x, y, w, h in detector.detect(frame):
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.imshow("Camera Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

reader.release()
cv2.destroyAllWindows()