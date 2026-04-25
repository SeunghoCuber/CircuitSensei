"""Camera capture utilities for Circuit-Sensei."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CaptureResult:
    """Result returned by a camera capture attempt."""

    path: str
    ok: bool
    message: str
    mock: bool = False


class CameraCapture:
    """Capture a top-down breadboard frame from OpenCV or a mock generator."""

    def __init__(self, camera_index: int = 0, mock_mode: bool = True) -> None:
        self.camera_index = camera_index
        self.mock_mode = mock_mode

    def capture(self, output_path: str | Path, image_size: tuple[int, int]) -> CaptureResult:
        """Capture a frame and save it to ``output_path``."""

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if self.mock_mode:
            self._write_mock_frame(output, image_size)
            return CaptureResult(
                path=str(output),
                ok=True,
                message="Mock breadboard frame captured.",
                mock=True,
            )

        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError:
            return CaptureResult(
                path=str(output),
                ok=False,
                message="OpenCV is not installed. Install requirements.txt or enable mock mode.",
            )

        camera = cv2.VideoCapture(self.camera_index)
        try:
            if not camera.isOpened():
                return CaptureResult(
                    path=str(output),
                    ok=False,
                    message=f"Webcam index {self.camera_index} could not be opened.",
                )

            ok, frame = camera.read()
            if not ok or frame is None:
                return CaptureResult(
                    path=str(output),
                    ok=False,
                    message="Webcam capture failed. Please describe the board placement manually.",
                )

            cv2.imwrite(str(output), frame)
            return CaptureResult(path=str(output), ok=True, message="Webcam frame captured.")
        finally:
            camera.release()

    def _write_mock_frame(self, output: Path, image_size: tuple[int, int]) -> None:
        """Create a synthetic breadboard image for offline development."""

        width, height = image_size
        try:
            import cv2  # type: ignore[import-not-found]
            import numpy as np  # type: ignore[import-not-found]

            frame = np.full((height, width, 3), 245, dtype=np.uint8)
            cv2.rectangle(frame, (80, 70), (width - 80, height - 70), (230, 230, 230), -1)
            cv2.rectangle(frame, (80, 70), (width - 80, height - 70), (120, 120, 120), 2)

            for x in range(110, width - 100, 17):
                for y in range(95, height - 95, 38):
                    cv2.circle(frame, (x, y), 3, (130, 130, 130), -1)
            cv2.line(frame, (90, height // 2), (width - 90, height // 2), (190, 190, 190), 3)
            cv2.putText(
                frame,
                "MOCK BREADBOARD",
                (95, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (70, 70, 70),
                2,
                cv2.LINE_AA,
            )
            cv2.imwrite(str(output), frame)
            return
        except ImportError:
            pass

        from PIL import Image, ImageDraw

        image = Image.new("RGB", (width, height), (245, 245, 245))
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 70, width - 80, height - 70), fill=(230, 230, 230), outline=(120, 120, 120), width=2)
        for x in range(110, width - 100, 17):
            for y in range(95, height - 95, 38):
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(130, 130, 130))
        draw.line((90, height // 2, width - 90, height // 2), fill=(190, 190, 190), width=3)
        draw.text((95, 30), "MOCK BREADBOARD", fill=(70, 70, 70))
        image.save(output, format="JPEG", quality=92)


def image_size_from_config(config: dict[str, Any]) -> tuple[int, int]:
    """Read ``breadboard.image_size`` as ``(width, height)``."""

    raw = config.get("breadboard", {}).get("image_size", [1280, 720])
    return int(raw[0]), int(raw[1])
