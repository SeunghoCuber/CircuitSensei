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
    brightness: float | None = None
    enhanced: bool = False


@dataclass(frozen=True)
class CameraSettings:
    """Runtime camera capture settings."""

    backend: str = "auto"
    warmup_frames: int = 20
    warmup_delay_seconds: float = 0.05
    width: int | None = None
    height: int | None = None
    brightness: float | None = None
    contrast: float | None = None
    exposure: float | None = None
    gain: float | None = None
    auto_enhance: bool = True
    dark_threshold: float = 85.0
    target_brightness: float = 135.0


class CameraCapture:
    """Capture a top-down breadboard frame from OpenCV or a mock generator."""

    def __init__(
        self,
        camera_index: int = 0,
        mock_mode: bool = True,
        settings: CameraSettings | None = None,
    ) -> None:
        self.camera_index = camera_index
        self.mock_mode = mock_mode
        self.settings = settings or CameraSettings()

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

        camera = self._open_camera(cv2)
        try:
            if not camera.isOpened():
                return CaptureResult(
                    path=str(output),
                    ok=False,
                    message=f"Webcam index {self.camera_index} could not be opened.",
                )

            self._apply_capture_settings(cv2, camera, image_size)
            ok = False
            frame = None
            for _ in range(max(1, self.settings.warmup_frames)):
                ok, frame = camera.read()
                if self.settings.warmup_delay_seconds > 0:
                    import time

                    time.sleep(self.settings.warmup_delay_seconds)
            if not ok or frame is None:
                return CaptureResult(
                    path=str(output),
                    ok=False,
                    message="Webcam capture failed. Please describe the board placement manually.",
                )

            brightness = self._brightness(cv2, frame)
            enhanced = False
            if self.settings.auto_enhance and brightness < self.settings.dark_threshold:
                frame = self._enhance_dark_frame(cv2, frame)
                brightness = self._brightness(cv2, frame)
                enhanced = True

            cv2.imwrite(str(output), frame)
            return CaptureResult(
                path=str(output),
                ok=True,
                message="Webcam frame captured.",
                brightness=round(float(brightness), 2),
                enhanced=enhanced,
            )
        finally:
            camera.release()

    def _open_camera(self, cv2: Any) -> Any:
        """Open a camera with a configured backend when available."""

        backend = self.settings.backend.lower().strip()
        if backend == "avfoundation" and hasattr(cv2, "CAP_AVFOUNDATION"):
            return cv2.VideoCapture(self.camera_index, cv2.CAP_AVFOUNDATION)
        if backend == "qt" and hasattr(cv2, "CAP_QT"):
            return cv2.VideoCapture(self.camera_index, cv2.CAP_QT)
        return cv2.VideoCapture(self.camera_index)

    def _apply_capture_settings(self, cv2: Any, camera: Any, image_size: tuple[int, int]) -> None:
        """Apply best-effort OpenCV camera properties."""

        width = self.settings.width or image_size[0]
        height = self.settings.height or image_size[1]
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))

        properties = [
            ("brightness", cv2.CAP_PROP_BRIGHTNESS),
            ("contrast", cv2.CAP_PROP_CONTRAST),
            ("exposure", cv2.CAP_PROP_EXPOSURE),
            ("gain", cv2.CAP_PROP_GAIN),
        ]
        for name, prop in properties:
            value = getattr(self.settings, name)
            if value is not None:
                camera.set(prop, float(value))

    def _brightness(self, cv2: Any, frame: Any) -> float:
        """Return mean luminance for a BGR frame."""

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(gray.mean())

    def _enhance_dark_frame(self, cv2: Any, frame: Any) -> Any:
        """Lift a dark frame enough for annotation and Gemini Vision."""

        brightness = max(self._brightness(cv2, frame), 1.0)
        gain = min(max(self.settings.target_brightness / brightness, 1.15), 3.0)
        lifted = cv2.convertScaleAbs(frame, alpha=gain, beta=10)
        gamma = 0.75
        try:
            import numpy as np  # type: ignore[import-not-found]

            table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype("uint8")
            return cv2.LUT(lifted, table)
        except ImportError:
            return lifted

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


def camera_settings_from_config(config: dict[str, Any]) -> CameraSettings:
    """Read optional camera capture settings from ``config.yaml``."""

    raw = config.get("camera", {})
    hardware = config.get("hardware", {})
    width = raw.get("width")
    height = raw.get("height")
    return CameraSettings(
        backend=str(raw.get("backend", "avfoundation")),
        warmup_frames=int(raw.get("warmup_frames", 20)),
        warmup_delay_seconds=float(raw.get("warmup_delay_seconds", 0.05)),
        width=int(width) if width is not None else None,
        height=int(height) if height is not None else None,
        brightness=_optional_float(raw.get("brightness")),
        contrast=_optional_float(raw.get("contrast")),
        exposure=_optional_float(raw.get("exposure")),
        gain=_optional_float(raw.get("gain")),
        auto_enhance=bool(raw.get("auto_enhance", True)),
        dark_threshold=float(raw.get("dark_threshold", hardware.get("dark_threshold", 85.0))),
        target_brightness=float(raw.get("target_brightness", 135.0)),
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
