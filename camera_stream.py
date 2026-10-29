import os
import threading
import time

# Silence FFmpeg decoder messages (e.g. "[h264 @ ...
# Printed when part of a frame is lost. -8 is AV_LOG_QUIET
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "8"

import cv2

class LatestFrameReader:
    """Reads the stream continuously so slow consumers always get the newest frame."""

    def __init__(self, url):
        backend = cv2.CAP_ANY if isinstance(url, int) else cv2.CAP_FFMPEG
        self.cap = cv2.VideoCapture(url, backend)
        self.opened = self.cap.isOpened()
        self._cond = threading.Condition()
        self._frame = None
        self._frame_id = 0
        self._last_returned = 0
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue
            with self._cond:
                self._frame = frame
                self._frame_id += 1
                self._cond.notify_all()

    def read(self, timeout=1.0):
        """Return the newest unseen frame, or None if none arrives within timeout."""
        with self._cond:
            if not self._cond.wait_for(
                lambda: self._frame_id > self._last_returned, timeout
            ):
                return None
            self._last_returned = self._frame_id
            return self._frame

    def release(self):
        self._running = False
        self._thread.join(timeout=2.0)
        self.cap.release()