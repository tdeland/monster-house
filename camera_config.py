import os
from pathlib import Path


def load_camera_source(env_file=None):
    """Load CAMERA_SOURCE from the process environment or the local .env file."""
    if env_file is None:
        env_file = Path(__file__).with_name(".env")
    else:
        env_file = Path(env_file)

    source = None
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            key, separator, value = line.partition("=")
            if separator and key.strip() == "CAMERA_SOURCE":
                source = value.strip()
                if len(source) >= 2 and source[0] == source[-1] and source[0] in ("'", '"'):
                    source = source[1:-1]
                break

    source = os.environ.get("CAMERA_SOURCE", source if source is not None else "0").strip()
    if not source:
        raise ValueError("CAMERA_SOURCE must not be empty.")
    return int(source) if source.isdecimal() else source
