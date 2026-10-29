import os
from camera_stream import LatestFrameReader
import cv2
from dotenv import load_dotenv
from person_detector import PersonDetector

load_dotenv()

camera_url = os.environ.get("CAMERA_SOURCE")
if not camera_url:
    raise SystemExit("CAMERA_SOURCE environment variable is not set.")

os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;udp")
detector = PersonDetector()
reader = LatestFrameReader(camera_url)
print("Camera stream opened: ", reader.opened)

while True:
    frame = reader.read(timeout=5)
    if frame is None:
        break
    boxes = detector.detect(frame)
    for (x,y,w,h) in boxes:
        cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 2)
    cv2.imshow("Camera Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

reader.release()
cv2.destroyAllWindows()