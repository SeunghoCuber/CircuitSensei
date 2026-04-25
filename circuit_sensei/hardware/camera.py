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
        mock_geometry: Any | None = None,
    ) -> None:
        self.camera_index = camera_index
        self.mock_mode = mock_mode
        self.settings = settings or CameraSettings()
        self.mock_geometry = mock_geometry

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

    def write_reference_frame(self, output_path: str | Path, image_size: tuple[int, int]) -> CaptureResult:
        """Write a clean generated breadboard reference frame."""

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self._write_mock_frame(output, image_size)
        return CaptureResult(
            path=str(output),
            ok=True,
            message="Reference breadboard frame generated.",
            mock=True,
        )

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
        if self.mock_geometry is not None:
            self._write_geometry_mock_frame(output, image_size)
            return

        board_left = round(width * 0.07)
        board_right = round(width * 0.93)
        board_top = round(height * 0.10)
        board_bottom = round(height * 0.88)
        hole_left = round(width * 0.17)
        hole_right = round(width * 0.83)
        hole_top = round(height * 0.18)
        hole_bottom = round(height * 0.82)
        center_x = (hole_left + hole_right) // 2
        gap = max(28, round(width * 0.035))
        left_rows = _even_positions(hole_left, center_x - gap // 2, 5)
        right_rows = _even_positions(center_x + gap // 2, hole_right, 5)
        row_positions = left_rows + right_rows
        col_positions = _even_positions(hole_top, hole_bottom, 30)

        try:
            import cv2  # type: ignore[import-not-found]
            import numpy as np  # type: ignore[import-not-found]

            frame = np.full((height, width, 3), (238, 240, 242), dtype=np.uint8)
            cv2.rectangle(frame, (board_left, board_top), (board_right, board_bottom), (246, 246, 244), -1)
            cv2.rectangle(frame, (board_left, board_top), (board_right, board_bottom), (122, 122, 118), 2)
            cv2.rectangle(
                frame,
                (board_left + 10, board_top + 10),
                (board_right - 10, board_top + 24),
                (230, 235, 255),
                -1,
            )
            cv2.rectangle(
                frame,
                (board_left + 10, board_bottom - 24),
                (board_right - 10, board_bottom - 10),
                (235, 245, 255),
                -1,
            )
            cv2.line(frame, (center_x, board_top + 15), (center_x, board_bottom - 15), (180, 180, 176), 5)
            cv2.rectangle(
                frame,
                (center_x - gap // 2 + 4, hole_top - 16),
                (center_x + gap // 2 - 4, hole_bottom + 16),
                (224, 224, 220),
                -1,
            )

            for index, x in enumerate(row_positions):
                row = DEFAULT_MOCK_ROWS[index]
                cv2.putText(frame, row, (x - 5, board_top + 46), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 80), 1)
                for y in col_positions:
                    cv2.circle(frame, (x, y), 3, (115, 115, 112), -1, cv2.LINE_AA)

            for label_col in (1, 5, 10, 15, 20, 25, 30):
                y = col_positions[label_col - 1]
                cv2.putText(frame, str(label_col), (board_left + 28, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (85, 85, 85), 1)

            cv2.putText(
                frame,
                "MOCK BREADBOARD",
                (board_left, max(32, board_top - 20)),
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

        image = Image.new("RGB", (width, height), (238, 240, 242))
        draw = ImageDraw.Draw(image)
        draw.rectangle((board_left, board_top, board_right, board_bottom), fill=(246, 246, 244), outline=(122, 122, 118), width=2)
        draw.rectangle((center_x - gap // 2 + 4, hole_top - 16, center_x + gap // 2 - 4, hole_bottom + 16), fill=(224, 224, 220))
        draw.line((center_x, board_top + 15, center_x, board_bottom - 15), fill=(180, 180, 176), width=5)
        for index, x in enumerate(row_positions):
            draw.text((x - 5, board_top + 34), DEFAULT_MOCK_ROWS[index], fill=(80, 80, 80))
            for y in col_positions:
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(115, 115, 112))
        for label_col in (1, 5, 10, 15, 20, 25, 30):
            y = col_positions[label_col - 1]
            draw.text((board_left + 28, y - 6), str(label_col), fill=(85, 85, 85))
        draw.text((board_left, max(18, board_top - 34)), "MOCK BREADBOARD", fill=(70, 70, 70))
        image.save(output, format="JPEG", quality=92)

    def _write_geometry_mock_frame(self, output: Path, image_size: tuple[int, int]) -> None:
        """Create a full Arduino + breadboard reference matching configured geometry."""

        from PIL import Image, ImageDraw

        width, height = image_size
        geometry = self.mock_geometry
        rows = tuple(getattr(geometry, "rows", DEFAULT_MOCK_ROWS))
        columns = int(getattr(geometry, "columns", 30))
        hole_positions = [
            geometry.hole_to_pixel(row, col)
            for row in rows
            for col in range(1, columns + 1)
        ]
        xs = [pos[0] for pos in hole_positions]
        ys = [pos[1] for pos in hole_positions]

        orientation = str(getattr(geometry, "orientation", "standard")).lower()
        if orientation in {"legacy", "rows_y", "columns_x"}:
            board = self._breadboard_bounds_for_legacy(width, height, xs, ys)
        else:
            board = self._breadboard_bounds_for_standard(width, height, xs, ys)

        image = Image.new("RGB", (width, height), (250, 250, 248))
        draw = ImageDraw.Draw(image)
        self._draw_arduino_reference(draw, board, image_size)
        self._draw_breadboard_reference(draw, board, geometry, rows, columns, orientation)
        image.save(output, format="JPEG", quality=94)

    @staticmethod
    def _breadboard_bounds_for_standard(
        width: int,
        height: int,
        xs: list[int],
        ys: list[int],
    ) -> tuple[int, int, int, int]:
        return (
            max(8, min(xs) - 86),
            max(8, min(ys) - 54),
            min(width - 8, max(xs) + 86),
            min(height - 8, max(ys) + 54),
        )

    @staticmethod
    def _breadboard_bounds_for_legacy(
        width: int,
        height: int,
        xs: list[int],
        ys: list[int],
    ) -> tuple[int, int, int, int]:
        return (
            max(8, min(xs) - 62),
            max(8, min(ys) - 68),
            min(width - 8, max(xs) + 62),
            min(height - 8, max(ys) + 68),
        )

    def _draw_breadboard_reference(
        self,
        draw: Any,
        board: tuple[int, int, int, int],
        geometry: Any,
        rows: tuple[str, ...],
        columns: int,
        orientation: str,
    ) -> None:
        board_left, board_top, board_right, board_bottom = board
        draw.rectangle(board, fill=(224, 224, 222), outline=(162, 162, 158), width=2)
        draw.rectangle((board_left + 10, board_top + 10, board_right - 10, board_bottom - 10), fill=(236, 236, 234))

        if orientation in {"legacy", "rows_y", "columns_x"}:
            left = geometry.hole_to_pixel(rows[0], 1)[0]
            right = geometry.hole_to_pixel(rows[0], columns)[0]
            e_y = geometry.hole_to_pixel("E", 1)[1] if "E" in rows else (board_top + board_bottom) // 2
            f_y = geometry.hole_to_pixel("F", 1)[1] if "F" in rows else e_y
            gap_y = (e_y + f_y) // 2
            draw.rectangle((left - 20, gap_y - 13, right + 20, gap_y + 13), fill=(205, 205, 202))
            self._draw_power_rails_legacy(draw, board, left, right)
        else:
            top = geometry.hole_to_pixel(rows[0], 1)[1]
            bottom = geometry.hole_to_pixel(rows[0], columns)[1]
            e_x = geometry.hole_to_pixel("E", 1)[0] if "E" in rows else (board_left + board_right) // 2
            f_x = geometry.hole_to_pixel("F", 1)[0] if "F" in rows else e_x
            gap_x = (e_x + f_x) // 2
            draw.rectangle((gap_x - 13, top - 20, gap_x + 13, bottom + 20), fill=(205, 205, 202))
            self._draw_power_rails_standard(draw, board, top, bottom)

        for row in rows:
            row_x, row_y = geometry.hole_to_pixel(row, 1)
            if orientation in {"legacy", "rows_y", "columns_x"}:
                draw.text((board_left + 14, row_y - 6), row, fill=(92, 92, 92))
                draw.text((board_right - 24, row_y - 6), row, fill=(92, 92, 92))
            else:
                draw.text((row_x - 5, board_top + 12), row, fill=(92, 92, 92))
                draw.text((row_x - 5, board_bottom - 24), row, fill=(92, 92, 92))
            for col in range(1, columns + 1):
                x, y = geometry.hole_to_pixel(row, col)
                self._draw_breadboard_hole(draw, x, y)

        label_cols = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
        label_cols = [col for col in label_cols if col <= columns]
        for col in label_cols:
            x, y = geometry.hole_to_pixel(rows[0], col)
            if orientation in {"legacy", "rows_y", "columns_x"}:
                draw.text((x - 8, board_top + 12), str(col), fill=(118, 118, 118))
                draw.text((x - 8, board_bottom - 28), str(col), fill=(118, 118, 118))
            else:
                draw.text((board_left + 16, y - 6), str(col), fill=(118, 118, 118))
                draw.text((board_right - 35, y - 6), str(col), fill=(118, 118, 118))

    def _draw_power_rails_standard(
        self,
        draw: Any,
        board: tuple[int, int, int, int],
        top: int,
        bottom: int,
    ) -> None:
        board_left, _, board_right, _ = board
        for pos_x, neg_x in ((board_left + 28, board_left + 55), (board_right - 55, board_right - 28)):
            draw.line((pos_x, top - 28, pos_x, bottom + 28), fill=(230, 60, 55), width=2)
            draw.line((neg_x, top - 28, neg_x, bottom + 28), fill=(50, 80, 220), width=2)
            draw.text((pos_x - 5, top - 48), "+", fill=(210, 50, 45))
            draw.text((neg_x - 4, top - 48), "-", fill=(45, 70, 190))
            for y in _even_positions(top, bottom, 25):
                self._draw_breadboard_hole(draw, pos_x, y)
                self._draw_breadboard_hole(draw, neg_x, y)

    def _draw_power_rails_legacy(
        self,
        draw: Any,
        board: tuple[int, int, int, int],
        left: int,
        right: int,
    ) -> None:
        _, board_top, _, board_bottom = board
        for pos_y, neg_y in ((board_top + 25, board_top + 48), (board_bottom - 48, board_bottom - 25)):
            draw.line((left - 28, pos_y, right + 28, pos_y), fill=(230, 60, 55), width=2)
            draw.line((left - 28, neg_y, right + 28, neg_y), fill=(50, 80, 220), width=2)
            draw.text((left - 50, pos_y - 7), "+", fill=(210, 50, 45))
            draw.text((left - 50, neg_y - 7), "-", fill=(45, 70, 190))
            for x in _even_positions(left, right, 25):
                self._draw_breadboard_hole(draw, x, pos_y)
                self._draw_breadboard_hole(draw, x, neg_y)

    @staticmethod
    def _draw_breadboard_hole(draw: Any, x: int, y: int) -> None:
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(202, 202, 198))
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(70, 70, 70))
        draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(28, 28, 28))

    def _draw_arduino_reference(
        self,
        draw: Any,
        breadboard: tuple[int, int, int, int],
        image_size: tuple[int, int],
    ) -> None:
        _, height = image_size
        board_left = 58
        board_top = max(105, breadboard[1] + 28)
        board_right = max(board_left + 430, min(breadboard[0] - 55, 525))
        board_bottom = min(height - 34, board_top + 548)
        teal = (20, 126, 148)
        dark = (42, 42, 42)

        try:
            draw.rounded_rectangle((board_left, board_top, board_right, board_bottom), radius=18, fill=teal)
        except AttributeError:
            draw.rectangle((board_left, board_top, board_right, board_bottom), fill=teal)

        usb = (board_left + 265, board_top - 30, board_left + 365, board_top + 78)
        draw.rectangle(usb, fill=(190, 190, 188), outline=(120, 120, 120), width=2)
        draw.rectangle((usb[0], usb[1], usb[2], usb[1] + 22), fill=(160, 160, 158))
        draw.rectangle((board_left + 28, board_top - 12, board_left + 100, board_top + 88), fill=(31, 31, 31), outline=(15, 15, 15), width=2)
        draw.rectangle((board_left + 40, board_top + 5, board_left + 92, board_top + 78), fill=(24, 24, 24))

        draw.rectangle((board_left + 120, board_top + 255, board_left + 170, board_top + 438), fill=dark)
        draw.rectangle((board_left + 295, board_top + 182, board_left + 340, board_top + 230), fill=dark)
        draw.ellipse((board_left + 70, board_top + 118, board_left + 125, board_top + 173), fill=(235, 235, 232), outline=dark, width=2)
        draw.ellipse((board_left + 70, board_top + 185, board_left + 125, board_top + 240), fill=(235, 235, 232), outline=dark, width=2)
        for x, y in (
            (board_right - 39, board_top + 127),
            (board_left + 33, board_top + 127),
            (board_left + 97, board_bottom - 23),
            (board_right - 100, board_bottom - 23),
        ):
            draw.ellipse((x - 15, y - 15, x + 15, y + 15), fill=(255, 255, 255))

        draw.text((board_left + 286, board_top + 305), "Arduino", fill=(255, 255, 255))
        draw.text((board_left + 326, board_top + 365), "UNO", fill=(255, 255, 255))
        draw.text((board_right - 94, board_top + 14), "RESET", fill=(255, 255, 255))
        draw.ellipse((board_right - 50, board_top + 20, board_right - 16, board_top + 54), fill=(132, 34, 32))

        self._draw_pin_header(draw, board_right - 42, board_top + 120, ["AREF", "GND", "13", "12", "~11", "~10", "~9", "8"], left_labels=True)
        self._draw_pin_header(draw, board_right - 42, board_top + 300, ["7", "~6", "~5", "4", "~3", "2", "TX1", "RX0"], left_labels=True)
        self._draw_pin_header(draw, board_left + 12, board_top + 245, ["IOREF", "RESET", "3V3", "5V", "GND", "GND", "VIN"], left_labels=False)
        self._draw_pin_header(draw, board_left + 12, board_top + 398, ["A0", "A1", "A2", "A3", "A4", "A5"], left_labels=False)

    @staticmethod
    def _draw_pin_header(draw: Any, x: int, y: int, labels: list[str], left_labels: bool) -> None:
        pitch = 22
        for index, label in enumerate(labels):
            yy = y + index * pitch
            draw.rectangle((x, yy, x + 16, yy + 16), fill=(18, 18, 18))
            draw.rectangle((x + 4, yy + 4, x + 12, yy + 12), fill=(75, 75, 75))
            if left_labels:
                draw.text((x - 42, yy + 1), label, fill=(255, 255, 255))
            else:
                draw.text((x + 23, yy + 1), label, fill=(255, 255, 255))


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


DEFAULT_MOCK_ROWS = tuple("ABCDEFGHIJ")


def _even_positions(start: int, end: int, count: int) -> list[int]:
    """Return ``count`` evenly spaced integer coordinates from start to end."""

    if count <= 1:
        return [start]
    step = (end - start) / (count - 1)
    return [round(start + index * step) for index in range(count)]
