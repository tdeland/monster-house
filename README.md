# Monster House

Monster House displays a pair of animated eyes that track people seen by a
camera. The eyes change from yellow to red when a person is detected and wander
when the camera has not seen anyone recently.

## Requirements

- Python 3
- OpenCV 4 (`opencv-python<5`; OpenCV 5 removed Darknet model support)
- Pygame
- YOLOv4-tiny model files for person detection

Install the Python packages:

```powershell
python -m pip install -r requirements.txt
```

## Camera configuration

The app uses webcam index `0` by default. To use another webcam, set its numeric
index in `.env`. To connect to an RTSP camera, set `CAMERA_SOURCE` to the stream
URL. Copy `.env.example` to `.env` and edit the value:

```dotenv
CAMERA_SOURCE="rtsp://username:password@192.168.1.100:554/stream1"
```

The `.env` file is ignored by Git. Keep camera credentials there and do not
commit them. A `CAMERA_SOURCE` value set in the process environment takes
precedence over the value in `.env`.

RTSP streams are decoded by OpenCV's FFmpeg backend over UDP, with a 10-second
open/read timeout. The app retries after a failed connection or stalled stream.
The installed OpenCV package must include FFmpeg support. Webcam indexes
continue to use OpenCV's camera capture. RTSP frames are processed at the
camera stream's configured resolution before YOLO inference.

## Run

### Person detection model

The `models` directory next to `main.py` contains `yolov4-tiny.cfg` and
`yolov4-tiny.weights`. If you need to download them again:

- [YOLOv4-tiny configuration](https://github.com/AlexeyAB/darknet/blob/master/cfg/yolov4-tiny.cfg)
- [YOLOv4-tiny weights](https://github.com/AlexeyAB/darknet/releases/download/yolov4/yolov4-tiny.weights)

Live camera mode checks for these files before starting. `--test` mode does not
require them.

Test the eyes in a window with mouse tracking. Hold the left mouse button to
make them angry:

```powershell
python main.py --test
```

Run with the configured camera in a borderless window:

```powershell
python main.py
```

For projection, configure the two projectors as an extended desktop side by
side. The application window spans both projectors, with one eye on each.

## Configuration

Display and tracking options, including eye size, projector position, mirroring,
and detection settings, are defined in the `CONFIG` section near the top of
`main.py`. Person detection is tuned for upright pedestrians farther from the
camera: it uses a 1920-pixel detection frame, a 512-pixel YOLO input, a 0.25
confidence threshold, and ignores detections wider than they are tall. The
aspect-ratio filter favors standing pedestrians and may exclude people who are
lying down or crouched. Tracking only accepts detections whose center lies in
the horizontal band covering the middle third of the frame's height.
