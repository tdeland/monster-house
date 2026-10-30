# Monster House

Monster House displays a pair of animated eyes that track people seen by a
camera. The eyes change from yellow to red when a person is detected and wander
when the camera has not seen anyone recently.

## Requirements

- Python 3
- OpenCV (`opencv-python<5`)
- Pygame
- Ultralytics YOLO (downloads `yolov8n.pt` on first run)

Install the Python packages:

```powershell
python -m pip install -r requirements.txt
```

## Camera configuration

The app loads `.env` from the project directory by default and uses webcam
index `0` if `CAMERA_SOURCE` is not set. To use another webcam, set its numeric
index in `.env`. To connect to an RTSP camera, set `CAMERA_SOURCE` to the stream
URL. Create `.env` and set the value:

```dotenv
CAMERA_SOURCE="rtsp://username:password@192.168.1.100:554/stream1"
```

The `.env` file is ignored by Git. Keep camera credentials there and do not
commit them. A `CAMERA_SOURCE` value set in the process environment takes
precedence over the value in `.env`; `--camera` overrides both for a single run.

RTSP streams are decoded by OpenCV's FFmpeg backend over TCP. Webcam indexes
and RTSP streams are read through the same OpenCV camera reader.

## Run

Test the eyes in a window with mouse tracking. Hold the left mouse button to
make them angry:

```powershell
python main.py --test
```

Run with the configured camera in a borderless window:

```powershell
python main.py
```

You can override `CAMERA_SOURCE` for one run with `--camera`, using a webcam
index or RTSP URL:

```powershell
python main.py --camera 1
python main.py --camera "rtsp://192.168.1.100:554/stream1"
```

For projection, configure the two projectors as an extended desktop side by
side. The application window spans both projectors, with one eye on each.

## Configuration

Display, eye appearance, tracking, and camera preview options are grouped in
the `CONFIG` section near the top of `main.py`. Camera preview guide lines mark
the middle third of the frame vertically; they are visual guides and do not
filter detections.
