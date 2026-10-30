import cv2

from camera_config import load_camera_source
from camera_stream import LatestFrameReader
from person_detector import PersonDetector

camera_source = load_camera_source()
detector = PersonDetector()
reader = LatestFrameReader(camera_source)
print("Camera stream opened:", reader.opened)

while True:
    frame = reader.read(timeout=5)
    if frame is None:
        break
    boxes = detector.detect(frame)
    for x, y, w, h in boxes:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.imshow("Camera Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

reader.release()
cv2.destroyAllWindows()