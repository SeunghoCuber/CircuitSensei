"""Breadboard geometry and image annotation tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ROWS = tuple("ABCDEFGHIJ")


@dataclass(frozen=True)
class BreadboardGeometry:
    """Map breadboard row and column names to image pixel coordinates."""

    top_left: tuple[int, int]
    bottom_right: tuple[int, int]
    rows: tuple[str, ...] = DEFAULT_ROWS
    columns: int = 63

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "BreadboardGeometry":
        """Build geometry from ``config.yaml`` breadboard calibration."""

        breadboard = config.get("breadboard", {})
        top_left = tuple(int(value) for value in breadboard.get("top_left", [110, 95]))
        bottom_right = tuple(int(value) for value in breadboard.get("bottom_right", [1170, 615]))
        rows = tuple(str(row).upper() for row in breadboard.get("rows", list(DEFAULT_ROWS)))
        columns = int(breadboard.get("columns", 63))
        return cls(top_left=top_left, bottom_right=bottom_right, rows=rows, columns=columns)

    def hole_to_pixel(self, row: str, col: int) -> tuple[int, int]:
        """Return approximate pixel coordinates for a breadboard hole."""

        row = row.upper().strip()
        if row not in self.rows:
            raise ValueError(f"Unknown breadboard row {row!r}. Expected one of {', '.join(self.rows)}.")
        if col < 1 or col > self.columns:
            raise ValueError(f"Column {col} is outside the configured 1-{self.columns} range.")

        x0, y0 = self.top_left
        x1, y1 = self.bottom_right
        x_step = 0 if self.columns == 1 else (x1 - x0) / (self.columns - 1)
        y_step = 0 if len(self.rows) == 1 else (y1 - y0) / (len(self.rows) - 1)
        x = round(x0 + (col - 1) * x_step)
        y = round(y0 + self.rows.index(row) * y_step)
        return x, y


class FrameAnnotator:
    """Draw Circuit-Sensei visual guidance onto a captured breadboard frame."""

    def __init__(self, geometry: BreadboardGeometry) -> None:
        self.geometry = geometry

    def annotate(self, frame_path: str | Path, output_path: str | Path, annotations: dict[str, Any]) -> dict[str, Any]:
        """Draw annotations and save the resulting image."""

        frame = Path(frame_path)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if not frame.exists():
            raise FileNotFoundError(f"Captured frame does not exist: {frame}")

        try:
            return self._annotate_with_cv2(frame, output, annotations)
        except ImportError:
            return self._annotate_with_pillow(frame, output, annotations)

    def _point(self, location: dict[str, Any]) -> tuple[int, int]:
        return self.geometry.hole_to_pixel(str(location["row"]), int(location["col"]))

    def _annotate_with_cv2(self, frame: Path, output: Path, annotations: dict[str, Any]) -> dict[str, Any]:
        import cv2  # type: ignore[import-not-found]

        image = cv2.imread(str(frame))
        if image is None:
            raise ValueError(f"Could not read image: {frame}")

        accent = (0, 190, 255)
        red = (35, 35, 230)
        green = (65, 180, 80)
        text = (25, 25, 25)

        for point in annotations.get("points", []):
            x, y = self._point(point)
            cv2.circle(image, (x, y), 18, accent, 3)
            cv2.circle(image, (x, y), 5, red, -1)
            label = str(point.get("label", f"{point.get('row')}{point.get('col')}"))
            cv2.putText(image, label, (x + 12, y - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.58, text, 2, cv2.LINE_AA)

        for arrow in annotations.get("arrows", []):
            start = self._point(arrow["from"])
            end = self._point(arrow["to"])
            cv2.arrowedLine(image, start, end, green, 4, cv2.LINE_AA, tipLength=0.08)
            label = str(arrow.get("label", ""))
            if label:
                mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
                cv2.putText(image, label, (mid[0] + 8, mid[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.62, text, 2, cv2.LINE_AA)

        step = annotations.get("step")
        message = str(annotations.get("message", "")).strip()
        banner = f"Step {step}: {message}" if step else message
        if banner:
            cv2.rectangle(image, (20, 18), (image.shape[1] - 20, 74), (255, 255, 255), -1)
            cv2.rectangle(image, (20, 18), (image.shape[1] - 20, 74), (70, 70, 70), 2)
            cv2.putText(image, banner[:120], (34, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.75, text, 2, cv2.LINE_AA)

        cv2.imwrite(str(output), image)
        return {"ok": True, "annotated_path": str(output), "backend": "opencv"}

    def _annotate_with_pillow(self, frame: Path, output: Path, annotations: dict[str, Any]) -> dict[str, Any]:
        from PIL import Image, ImageDraw

        image = Image.open(frame).convert("RGB")
        draw = ImageDraw.Draw(image)
        accent = (255, 190, 0)
        red = (230, 35, 35)
        green = (80, 180, 65)
        text = (25, 25, 25)

        for point in annotations.get("points", []):
            x, y = self._point(point)
            draw.ellipse((x - 18, y - 18, x + 18, y + 18), outline=accent, width=3)
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=red)
            label = str(point.get("label", f"{point.get('row')}{point.get('col')}"))
            draw.text((x + 12, y - 28), label, fill=text)

        for arrow in annotations.get("arrows", []):
            start = self._point(arrow["from"])
            end = self._point(arrow["to"])
            draw.line((*start, *end), fill=green, width=4)
            self._draw_arrow_head(draw, start, end, green)
            label = str(arrow.get("label", ""))
            if label:
                mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
                draw.text((mid[0] + 8, mid[1] - 20), label, fill=text)

        step = annotations.get("step")
        message = str(annotations.get("message", "")).strip()
        banner = f"Step {step}: {message}" if step else message
        if banner:
            draw.rectangle((20, 18, image.width - 20, 74), fill=(255, 255, 255), outline=(70, 70, 70), width=2)
            draw.text((34, 38), banner[:120], fill=text)

        image.save(output, format="JPEG", quality=92)
        return {"ok": True, "annotated_path": str(output), "backend": "pillow"}

    def _draw_arrow_head(
        self,
        draw: Any,
        start: tuple[int, int],
        end: tuple[int, int],
        color: tuple[int, int, int],
    ) -> None:
        import math

        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        length = 18
        spread = math.pi / 7
        points = [end]
        for sign in (1, -1):
            points.append(
                (
                    round(end[0] - length * math.cos(angle + sign * spread)),
                    round(end[1] - length * math.sin(angle + sign * spread)),
                )
            )
        draw.polygon(points, fill=color)
