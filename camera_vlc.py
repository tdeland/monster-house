import ctypes
import os
from pathlib import Path
import threading

import numpy as np


_VLC_DLL_HANDLES = []


def _prepare_vlc_runtime():
    if os.name != "nt":
        return

    install_roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
    ]
    for root in install_roots:
        if not root:
            continue
        vlc_dir = Path(root) / "VideoLAN" / "VLC"
        if (vlc_dir / "libvlc.dll").is_file():
            _VLC_DLL_HANDLES.append(os.add_dll_directory(str(vlc_dir)))
            plugin_dir = vlc_dir / "plugins"
            if plugin_dir.is_dir():
                os.environ.setdefault("VLC_PLUGIN_PATH", str(plugin_dir))
            return


_prepare_vlc_runtime()
import vlc


class VlcRtspCapture:
    def __init__(self, source, width, height, read_timeout_ms):
        self.width = width
        self.height = height
        self.read_timeout = read_timeout_ms / 1000
        self._buffer = (ctypes.c_ubyte * (width * height * 4))()
        self._frame_lock = threading.Lock()
        self._frame_ready = threading.Event()
        self._latest_frame = None
        self._instance = vlc.Instance("--intf=dummy", "--no-audio", "--quiet")
        if self._instance is None:
            raise RuntimeError("Could not initialize VLC. Check that VLC is installed.")

        self._player = self._instance.media_player_new()
        media = self._instance.media_new(source)
        self._player.set_media(media)
        self._lock_callback = vlc.CallbackDecorators.VideoLockCb(self._lock_video)
        self._unlock_callback = vlc.CallbackDecorators.VideoUnlockCb(self._unlock_video)
        self._display_callback = vlc.CallbackDecorators.VideoDisplayCb(self._display_video)
        self._player.video_set_callbacks(
            self._lock_callback,
            self._unlock_callback,
            self._display_callback,
            None,
        )
        self._player.video_set_format(
            "RV32",
            self.width,
            self.height,
            self.width * 4,
        )
        if self._player.play() == -1:
            self.release()
            raise RuntimeError("VLC could not start the RTSP stream.")

    def _lock_video(self, _opaque, planes):
        planes[0] = ctypes.cast(self._buffer, ctypes.c_void_p)
        return None

    def _unlock_video(self, _opaque, _picture, _planes):
        frame = np.ctypeslib.as_array(self._buffer).reshape(
            self.height,
            self.width,
            4,
        )[:, :, :3].copy()
        with self._frame_lock:
            self._latest_frame = frame
            self._frame_ready.set()

    def _display_video(self, _opaque, _picture):
        pass

    def isOpened(self):
        return self._player is not None

    def read(self):
        if not self._frame_ready.wait(self.read_timeout):
            return False, None
        with self._frame_lock:
            self._frame_ready.clear()
            if self._latest_frame is None:
                return False, None
            return True, self._latest_frame.copy()

    def release(self):
        if self._player is not None:
            self._player.stop()
            self._player.release()
            self._player = None
        if self._instance is not None:
            self._instance.release()
            self._instance = None
        self._frame_ready.set()
