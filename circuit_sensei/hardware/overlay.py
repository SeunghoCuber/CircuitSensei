"""Breadboard geometry and image annotation tools."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any


DEFAULT_ROWS = tuple("ABCDEFGHIJ")
TOP_BANK_ROWS = tuple("ABCDE")
BOTTOM_BANK_ROWS = tuple("FGHIJ")
POWER_RAIL_POSITIVE_ALIASES = {"positive", "+", "plus", "pos", "5v", "vcc"}
POWER_RAIL_NEGATIVE_ALIASES = {"negative", "-", "minus", "neg", "gnd", "ground"}


@dataclass(frozen=True)
class AnnotationStyle:
    """Visual style for generated breadboard annotations."""

    point_radius: int = 20
    point_inner_radius: int = 6
    arrow_thickness: int = 5
    carry_wire_thickness: int = 4
    point_outline_thickness: int = 4
    node_line_thickness: int = 7
    label_padding: int = 7
    label_font_scale: float = 0.58
    arrow_label_font_scale: float = 0.56
    banner_font_scale: float = 0.72
    banner_position: str = "bottom"
    banner_max_lines: int = 3

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "AnnotationStyle":
        """Read optional annotation style overrides from ``config.yaml``."""

        raw = config.get("overlay", {})
        return cls(
            point_radius=int(raw.get("point_radius", 20)),
            point_inner_radius=int(raw.get("point_inner_radius", 6)),
            arrow_thickness=int(raw.get("arrow_thickness", 5)),
            carry_wire_thickness=int(raw.get("carry_wire_thickness", 4)),
            point_outline_thickness=int(raw.get("point_outline_thickness", 4)),
            node_line_thickness=int(raw.get("node_line_thickness", 7)),
            label_padding=int(raw.get("label_padding", 7)),
            label_font_scale=float(raw.get("label_font_scale", 0.58)),
            arrow_label_font_scale=float(raw.get("arrow_label_font_scale", 0.56)),
            banner_font_scale=float(raw.get("banner_font_scale", 0.72)),
            banner_position=str(raw.get("banner_position", "bottom")),
            banner_max_lines=int(raw.get("banner_max_lines", 3)),
        )


@dataclass(frozen=True)
class BreadboardGeometry:
    """Map breadboard row and column names to image pixel coordinates."""

    top_left: tuple[int, int]
    bottom_right: tuple[int, int]
    rows: tuple[str, ...] = DEFAULT_ROWS
    columns: int = 63
    orientation: str = "standard"
    row_x_positions: tuple[int, ...] = ()

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "BreadboardGeometry":
        """Build geometry from ``config.yaml`` breadboard calibration."""

        breadboard = config.get("breadboard", {})
        top_left = tuple(int(value) for value in breadboard.get("top_left", [110, 95]))
        bottom_right = tuple(int(value) for value in breadboard.get("bottom_right", [1170, 615]))
        rows = tuple(str(row).upper() for row in breadboard.get("rows", list(DEFAULT_ROWS)))
        columns = int(breadboard.get("columns", 63))
        orientation = str(breadboard.get("orientation", "standard")).lower().strip()
        row_x_positions = tuple(int(x) for x in breadboard.get("row_x_positions", []))
        return cls(
            top_left=top_left,
            bottom_right=bottom_right,
            rows=rows,
            columns=columns,
            orientation=orientation,
            row_x_positions=row_x_positions,
        )

    def hole_to_pixel(self, row: str, col: int) -> tuple[int, int]:
        """Return approximate pixel coordinates for a breadboard hole."""

        row = row.upper().strip()
        if row not in self.rows:
            raise ValueError(f"Unknown breadboard row {row!r}. Expected one of {', '.join(self.rows)}.")
        if col < 1 or col > self.columns:
            raise ValueError(f"Column {col} is outside the configured 1-{self.columns} range.")

        x0, y0 = self.top_left
        x1, y1 = self.bottom_right
        if self.orientation in {"legacy", "rows_y", "columns_x"}:
            x_step = 0 if self.columns == 1 else (x1 - x0) / (self.columns - 1)
            y_step = 0 if len(self.rows) == 1 else (y1 - y0) / (len(self.rows) - 1)
            x = round(x0 + (col - 1) * x_step)
            y = round(y0 + self.rows.index(row) * y_step)
            return x, y

        # Use exact per-row x positions when provided (handles centre-gap between banks)
        if self.row_x_positions and len(self.row_x_positions) == len(self.rows):
            x = self.row_x_positions[self.rows.index(row)]
        else:
            x_step = 0 if len(self.rows) == 1 else (x1 - x0) / (len(self.rows) - 1)
            x = round(x0 + self.rows.index(row) * x_step)

        y_step = 0 if self.columns == 1 else (y1 - y0) / (self.columns - 1)
        y = round(y0 + (col - 1) * y_step)
        return x, y

    def bank_for_row(self, row: str) -> str:
        """Return the breadboard terminal bank for a row."""

        row = row.upper().strip()
        if row in TOP_BANK_ROWS:
            return "top"
        if row in BOTTOM_BANK_ROWS:
            return "bottom"
        raise ValueError(f"Unknown breadboard row {row!r}.")

    def node_key(self, row: str, col: int) -> tuple[str, int]:
        """Return the electrical node key for a breadboard hole."""

        return self.bank_for_row(row), int(col)

    def connected_rows(self, row: str) -> tuple[str, ...]:
        """Return rows connected to ``row`` at the same column."""

        row = row.upper().strip()
        if row in TOP_BANK_ROWS:
            return tuple(candidate for candidate in TOP_BANK_ROWS if candidate in self.rows)
        if row in BOTTOM_BANK_ROWS:
            return tuple(candidate for candidate in BOTTOM_BANK_ROWS if candidate in self.rows)
        return (row,)

    def node_span_pixels(self, row: str, col: int) -> tuple[tuple[int, int], tuple[int, int]]:
        """Return first and last pixel in the connected terminal strip node."""

        rows = self.connected_rows(row)
        return self.hole_to_pixel(rows[0], col), self.hole_to_pixel(rows[-1], col)

    def rail_to_pixel(self, rail: str, col: int | None = None, side: str | None = None) -> tuple[int, int]:
        """Return approximate pixel coordinates for a power rail hole marker."""

        normalized_col = self._normalized_col(col)
        normalized_rail = self._normalized_rail(rail)
        normalized_side = (side or "").strip().lower()

        if self.orientation in {"legacy", "rows_y", "columns_x"}:
            x = self.hole_to_pixel(self.rows[0], normalized_col)[0]
            top_y = self.hole_to_pixel(self.rows[0], 1)[1]
            bottom_y = self.hole_to_pixel(self.rows[0], self.columns)[1]
            if normalized_side not in {"", "top", "bottom"}:
                raise ValueError(f"Unknown legacy rail side {side!r}; expected 'top' or 'bottom'.")
            side_key = normalized_side or "top"
            if side_key == "top":
                y = top_y - 43 if normalized_rail == "positive" else top_y - 20
            else:
                y = bottom_y + 20 if normalized_rail == "positive" else bottom_y + 43
            return x, y

        y = self.hole_to_pixel(self.rows[0], normalized_col)[1]
        min_x = min(self.hole_to_pixel(row, 1)[0] for row in self.rows)
        max_x = max(self.hole_to_pixel(row, 1)[0] for row in self.rows)
        if normalized_side not in {"", "left", "right"}:
            raise ValueError(f"Unknown rail side {side!r}; expected 'left' or 'right'.")
        side_key = normalized_side or "left"
        if side_key == "left":
            x = min_x - 58 if normalized_rail == "positive" else min_x - 31
        else:
            x = max_x + 31 if normalized_rail == "positive" else max_x + 58
        return x, y

    def _normalized_col(self, col: int | None) -> int:
        if col is None:
            return max(1, min(self.columns, 3))
        normalized = int(col)
        if normalized < 1 or normalized > self.columns:
            raise ValueError(f"Rail column {normalized} is outside the configured 1-{self.columns} range.")
        return normalized

    @staticmethod
    def _normalized_rail(rail: str) -> str:
        value = rail.strip().lower()
        if value in POWER_RAIL_POSITIVE_ALIASES:
            return "positive"
        if value in POWER_RAIL_NEGATIVE_ALIASES:
            return "negative"
        raise ValueError(f"Unknown rail {rail!r}; expected positive/+ or negative/GND.")


class FrameAnnotator:
    """Draw Circuit-Sensei visual guidance onto a captured breadboard frame."""

    def __init__(self, geometry: BreadboardGeometry, style: AnnotationStyle | None = None) -> None:
        self.geometry = geometry
        self.style = style or AnnotationStyle()

    def annotate(self, frame_path: str | Path, output_path: str | Path, annotations: dict[str, Any]) -> dict[str, Any]:
        """Draw annotations and save the resulting image."""

        frame = Path(frame_path)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if not frame.exists():
            raise FileNotFoundError(f"Captured frame does not exist: {frame}")

        warnings = self.validate_annotations(annotations)
        try:
            return self._annotate_with_cv2(frame, output, annotations, warnings)
        except ImportError:
            return self._annotate_with_pillow(frame, output, annotations, warnings)

    def validate_annotations(self, annotations: dict[str, Any]) -> list[str]:
        """Return non-fatal warnings about ambiguous physical guidance."""

        warnings: list[str] = []
        occupied: dict[tuple[str, int], str] = {}
        for point in self._annotation_points(annotations):
            try:
                self._point(point)
            except (KeyError, TypeError, ValueError) as exc:
                warnings.append(f"Invalid point annotation {point!r}: {exc}")
                continue

            location = self._hole_location(point)
            if location is None:
                continue

            row, col = location
            label = str(point.get("label", f"{row}{col}"))
            key = location
            if key in occupied:
                warnings.append(
                    f"Two physical leads target exact same hole {row}{col}: "
                    f"{occupied[key]!r} and {label!r}."
                )
            else:
                occupied[key] = label

        for arrow in self._annotation_arrows(annotations):
            try:
                self._point(arrow["from"])
                self._point(arrow["to"])
            except (KeyError, TypeError, ValueError) as exc:
                warnings.append(f"Invalid arrow annotation {arrow!r}: {exc}")
                continue

            start_hole = self._hole_location(arrow["from"])
            end_hole = self._hole_location(arrow["to"])
            if start_hole is None or end_hole is None:
                continue

            start_row, start_col = start_hole
            end_row, end_col = end_hole
            if (start_row, start_col) == (end_row, end_col):
                warnings.append(f"Arrow {arrow.get('label', '')!r} starts and ends on {start_row}{start_col}.")
            if start_col == end_col:
                try:
                    if self.geometry.bank_for_row(start_row) != self.geometry.bank_for_row(end_row):
                        warnings.append(
                            f"Arrow {arrow.get('label', '')!r} crosses the E/F center gap at column {start_col}; "
                            "treat it as a jumper, not an internal breadboard connection."
                        )
                except ValueError:
                    pass
        return warnings

    def _point(self, location: dict[str, Any]) -> tuple[int, int]:
        hole = self._hole_location(location)
        if hole is not None:
            return self.geometry.hole_to_pixel(hole[0], hole[1])

        if "rail" in location:
            col = location.get("col")
            rail_col = int(col) if col is not None else None
            side = location.get("side")
            side_value = str(side) if side is not None else None
            return self.geometry.rail_to_pixel(str(location["rail"]), rail_col, side_value)

        if "x" in location and "y" in location:
            return int(location["x"]), int(location["y"])

        raise ValueError("Location must provide row/col, rail, or x/y coordinates.")

    def _annotate_with_cv2(
        self,
        frame: Path,
        output: Path,
        annotations: dict[str, Any],
        warnings: list[str],
    ) -> dict[str, Any]:
        import cv2  # type: ignore[import-not-found]

        image = cv2.imread(str(frame))
        if image is None:
            raise ValueError(f"Could not read image: {frame}")

        points = self._annotation_points(annotations)
        arrows = self._annotation_arrows(annotations)
        carryover_wires = self._annotation_carryover_wires(annotations)
        occupied_labels: list[tuple[int, int, int, int]] = []

        for wire in carryover_wires:
            start = self._point(wire["from"])
            end = self._point(wire["to"])
            self._draw_wire_cv2(
                cv2,
                image,
                start,
                end,
                color=(196, 164, 112),
                thickness=self.style.carry_wire_thickness,
                draw_arrow=False,
                shorten_inset=max(2, self.style.point_radius // 3),
            )

        for arrow in arrows:
            start = self._point(arrow["from"])
            end = self._point(arrow["to"])
            self._draw_wire_cv2(
                cv2,
                image,
                start,
                end,
                color=(126, 206, 78),
                thickness=self.style.arrow_thickness,
                draw_arrow=True,
                shorten_inset=self.style.point_radius + 5,
            )
            label = str(arrow.get("label", "")).strip()
            if label:
                mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
                self._draw_label_cv2(
                    cv2,
                    image,
                    mid,
                    label,
                    occupied_labels,
                    font_scale=self.style.arrow_label_font_scale,
                    accent=(126, 206, 78),
                )

        for point in points:
            x, y = self._point(point)
            self._draw_target_hole_cv2(cv2, image, (x, y))

        for point in points:
            x, y = self._point(point)
            display = self._point_display_label(point)
            self._draw_label_cv2(cv2, image, (x, y), display, occupied_labels)

        cv2.imwrite(str(output), image)
        return {
            "ok": True,
            "annotated_path": str(output),
            "backend": "opencv",
            "points": len(points),
            "arrows": len(arrows),
            "carryover_wires": len(carryover_wires),
            "warnings": warnings,
        }

    def _annotate_with_pillow(
        self,
        frame: Path,
        output: Path,
        annotations: dict[str, Any],
        warnings: list[str],
    ) -> dict[str, Any]:
        from PIL import Image, ImageDraw

        image = Image.open(frame).convert("RGB")
        draw = ImageDraw.Draw(image)
        points = self._annotation_points(annotations)
        arrows = self._annotation_arrows(annotations)
        carryover_wires = self._annotation_carryover_wires(annotations)
        occupied_labels: list[tuple[int, int, int, int]] = []

        for wire in carryover_wires:
            start = self._point(wire["from"])
            end = self._point(wire["to"])
            self._draw_wire_pillow(
                draw,
                start,
                end,
                color=(112, 164, 196),
                thickness=self.style.carry_wire_thickness,
                draw_arrow=False,
                shorten_inset=max(2, self.style.point_radius // 3),
            )

        for arrow in arrows:
            start = self._point(arrow["from"])
            end = self._point(arrow["to"])
            self._draw_wire_pillow(
                draw,
                start,
                end,
                color=(78, 206, 126),
                thickness=self.style.arrow_thickness,
                draw_arrow=True,
                shorten_inset=self.style.point_radius + 4,
            )
            label = str(arrow.get("label", "")).strip()
            if label:
                mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
                self._draw_label_pillow(draw, image.size, mid, label, occupied_labels)

        for point in points:
            x, y = self._point(point)
            r = self.style.point_radius
            # Drop shadow
            draw.ellipse((x - r + 2, y - r + 2, x + r + 2, y + r + 2), fill=(20, 20, 20))
            # Emerald filled dot
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(16, 185, 129), outline=(56, 189, 248), width=2)

        for point in points:
            x, y = self._point(point)
            display = self._point_display_label(point)
            self._draw_label_pillow(draw, image.size, (x, y), display, occupied_labels)

        image.save(output, format="JPEG", quality=92)
        return {
            "ok": True,
            "annotated_path": str(output),
            "backend": "pillow",
            "points": len(points),
            "arrows": len(arrows),
            "carryover_wires": len(carryover_wires),
            "warnings": warnings,
        }

    @staticmethod
    def _annotation_points(annotations: dict[str, Any]) -> list[dict[str, Any]]:
        return [point for point in annotations.get("points", []) if isinstance(point, dict)]

    @staticmethod
    def _annotation_arrows(annotations: dict[str, Any]) -> list[dict[str, Any]]:
        arrows: list[dict[str, Any]] = []
        for arrow in annotations.get("arrows", []):
            if isinstance(arrow, dict) and isinstance(arrow.get("from"), dict) and isinstance(arrow.get("to"), dict):
                arrows.append(arrow)
        return arrows

    @staticmethod
    def _annotation_carryover_wires(annotations: dict[str, Any]) -> list[dict[str, Any]]:
        wires: list[dict[str, Any]] = []
        for key in ("carryover_wires", "persistent_wires"):
            for wire in annotations.get(key, []):
                if isinstance(wire, dict) and isinstance(wire.get("from"), dict) and isinstance(wire.get("to"), dict):
                    wires.append(wire)
        return wires

    @staticmethod
    def _banner_text(annotations: dict[str, Any]) -> str:
        step = annotations.get("step")
        message = str(annotations.get("message", "")).strip()
        if step and message:
            return f"Step {step}: {message}"
        return message

    def _draw_node_spans_cv2(self, cv2: Any, image: Any, points: list[dict[str, Any]]) -> None:
        overlay = image.copy()
        drawn: set[tuple[str, int]] = set()
        for point in points:
            hole = self._hole_location(point)
            if hole is None:
                continue
            row, col = hole
            key = self.geometry.node_key(row, col)
            if key in drawn:
                continue
            drawn.add(key)
            start, end = self.geometry.node_span_pixels(row, col)
            cv2.line(overlay, start, end, (75, 220, 255), self.style.node_line_thickness, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.35, image, 0.65, 0, image)

    @staticmethod
    def _hole_location(location: dict[str, Any]) -> tuple[str, int] | None:
        if "row" not in location or "col" not in location:
            return None
        row = str(location["row"]).upper().strip()
        col = int(location["col"])
        return row, col

    @staticmethod
    def _point_display_label(point: dict[str, Any]) -> str:
        label = str(point.get("label", "")).strip()
        hole = FrameAnnotator._hole_location(point)
        if hole is not None:
            coordinate = f"{hole[0]}{hole[1]}"
            if not label:
                return coordinate
            return f"{label} ({coordinate})" if coordinate not in label else label

        if "rail" in point:
            side = str(point.get("side", "left")).lower().strip()
            side_text = f" {side}" if side else ""
            col = point.get("col")
            col_text = f" col {col}" if col not in {None, ""} else ""
            rail_text = str(point.get("rail", "rail")).strip()
            rail_label = f"{rail_text}{side_text}{col_text}".strip()
            return label or rail_label

        if "x" in point and "y" in point:
            coordinate = f"({int(point['x'])}, {int(point['y'])})"
            return label or coordinate

        return label or "target"

    def _draw_wire_cv2(
        self,
        cv2: Any,
        image: Any,
        start: tuple[int, int],
        end: tuple[int, int],
        color: tuple[int, int, int],
        thickness: int,
        draw_arrow: bool,
        shorten_inset: int,
    ) -> None:
        line_start, line_end = self._shortened_line(start, end, shorten_inset)
        shadow_start = (line_start[0] + 2, line_start[1] + 2)
        shadow_end = (line_end[0] + 2, line_end[1] + 2)
        shadow_thickness = max(2, thickness + 2)
        if draw_arrow:
            cv2.arrowedLine(
                image,
                shadow_start,
                shadow_end,
                (34, 34, 34),
                shadow_thickness,
                cv2.LINE_AA,
                tipLength=0.08,
            )
            cv2.arrowedLine(
                image,
                line_start,
                line_end,
                color,
                thickness,
                cv2.LINE_AA,
                tipLength=0.08,
            )
            return

        cv2.line(image, shadow_start, shadow_end, (34, 34, 34), shadow_thickness, cv2.LINE_AA)
        cv2.line(image, line_start, line_end, color, thickness, cv2.LINE_AA)

    def _draw_target_hole_cv2(self, cv2: Any, image: Any, center: tuple[int, int]) -> None:
        x, y = center
        r = self.style.point_radius
        # Drop shadow
        cv2.circle(image, (x + 2, y + 2), r, (20, 20, 20), -1, cv2.LINE_AA)
        # Emerald filled dot
        cv2.circle(image, center, r, (129, 185, 16), -1, cv2.LINE_AA)
        # Thin cyan border
        cv2.circle(image, center, r, (248, 189, 56), 2, cv2.LINE_AA)

    def _draw_label_cv2(
        self,
        cv2: Any,
        image: Any,
        anchor: tuple[int, int],
        text: str,
        occupied: list[tuple[int, int, int, int]],
        font_scale: float | None = None,
        accent: tuple[int, int, int] = (129, 185, 16),
    ) -> None:
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = self.style.label_font_scale if font_scale is None else font_scale
        thickness = 2
        label = text[:80]
        (text_width, text_height), baseline = cv2.getTextSize(label, font, scale, thickness)
        pad = self.style.label_padding
        while text_width + pad * 2 > image.shape[1] - 12 and len(label) > 8:
            label = label[:-4].rstrip() + "..."
            (text_width, text_height), baseline = cv2.getTextSize(label, font, scale, thickness)
        rect = self._label_rect(anchor, text_width, text_height + baseline, image.shape[1], image.shape[0], occupied)
        x0, y0, x1, y1 = rect
        occupied.append(rect)

        cv2.line(image, anchor, self._nearest_rect_point(anchor, rect), (68, 73, 80), 2, cv2.LINE_AA)
        cv2.rectangle(image, (x0 + 2, y0 + 2), (x1 + 2, y1 + 2), (22, 22, 22), -1)
        cv2.rectangle(image, (x0, y0), (x1, y1), (35, 39, 44), -1)
        cv2.rectangle(image, (x0, y0), (x1, y1), accent, 2)
        cv2.putText(image, label, (x0 + pad, y1 - pad - baseline), font, scale, (236, 239, 243), thickness, cv2.LINE_AA)

    def _draw_banner_cv2(self, cv2: Any, image: Any, text: str) -> None:
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = 2
        max_width = image.shape[1] - 90
        lines = self._wrap_cv2_text(cv2, text, max_width, font, self.style.banner_font_scale, thickness)
        line_height = max(28, int(34 * self.style.banner_font_scale))
        banner_height = 28 + line_height * len(lines)
        if self.style.banner_position.lower() == "top":
            y0 = 18
        else:
            y0 = max(18, image.shape[0] - banner_height - 18)
        y1 = y0 + banner_height
        cv2.rectangle(image, (25, y0 + 3), (image.shape[1] - 19, y1 + 3), (20, 20, 20), -1)
        cv2.rectangle(image, (22, y0), (image.shape[1] - 22, y1), (28, 33, 38), -1)
        cv2.rectangle(image, (22, y0), (image.shape[1] - 22, y1), (88, 96, 106), 2)
        cv2.rectangle(image, (22, y0), (34, y1), (129, 185, 16), -1)
        y = y0 + 28
        for line in lines:
            cv2.putText(image, line, (48, y), font, self.style.banner_font_scale, (236, 239, 243), thickness, cv2.LINE_AA)
            y += line_height

    def _draw_label_pillow(
        self,
        draw: Any,
        image_size: tuple[int, int],
        anchor: tuple[int, int],
        text: str,
        occupied: list[tuple[int, int, int, int]],
    ) -> None:
        label = text[:80]
        bbox = draw.textbbox((0, 0), label)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        while width + self.style.label_padding * 2 > image_size[0] - 12 and len(label) > 8:
            label = label[:-4].rstrip() + "..."
            bbox = draw.textbbox((0, 0), label)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
        rect = self._label_rect(anchor, width, height, image_size[0], image_size[1], occupied)
        x0, y0, x1, y1 = rect
        occupied.append(rect)
        draw.line((*anchor, *self._nearest_rect_point(anchor, rect)), fill=(68, 73, 80), width=2)
        draw.rectangle((x0 + 2, y0 + 2, x1 + 2, y1 + 2), fill=(22, 22, 22))
        draw.rectangle(rect, fill=(35, 39, 44), outline=(16, 185, 129), width=2)
        draw.text((x0 + self.style.label_padding, y0 + self.style.label_padding), label, fill=(236, 239, 243))

    def _draw_banner_pillow(self, draw: Any, image_size: tuple[int, int], text: str) -> None:
        width, height = image_size
        lines = self._wrap_plain_text(text, 95)[: self.style.banner_max_lines]
        line_height = 18
        banner_height = 24 + line_height * len(lines)
        y0 = 18 if self.style.banner_position.lower() == "top" else max(18, height - banner_height - 18)
        y1 = y0 + banner_height
        draw.rectangle((25, y0 + 3, width - 19, y1 + 3), fill=(20, 20, 20))
        draw.rectangle((22, y0, width - 22, y1), fill=(28, 33, 38), outline=(88, 96, 106), width=2)
        draw.rectangle((22, y0, 34, y1), fill=(16, 185, 129))
        y = y0 + 12
        for line in lines:
            draw.text((48, y), line, fill=(236, 239, 243))
            y += line_height

    def _draw_wire_pillow(
        self,
        draw: Any,
        start: tuple[int, int],
        end: tuple[int, int],
        color: tuple[int, int, int],
        thickness: int,
        draw_arrow: bool,
        shorten_inset: int,
    ) -> None:
        shortened = self._shortened_line(start, end, shorten_inset)
        draw.line((*shortened[0], *shortened[1]), fill=(34, 34, 34), width=max(2, thickness + 2))
        draw.line((*shortened[0], *shortened[1]), fill=color, width=thickness)
        if draw_arrow:
            self._draw_arrow_head(draw, shortened[0], shortened[1], color)

    def _label_rect(
        self,
        anchor: tuple[int, int],
        text_width: int,
        text_height: int,
        image_width: int,
        image_height: int,
        occupied: list[tuple[int, int, int, int]],
    ) -> tuple[int, int, int, int]:
        pad = self.style.label_padding
        width = text_width + pad * 2
        height = text_height + pad * 2
        ax, ay = anchor
        offsets = [
            (26, -height - 10),
            (26, 14),
            (-width - 26, -height - 10),
            (-width - 26, 14),
            (-width // 2, -height - 30),
            (-width // 2, 30),
        ]
        for dx, dy in offsets:
            rect = self._clamp_rect((ax + dx, ay + dy, ax + dx + width, ay + dy + height), image_width, image_height)
            if not any(self._rects_intersect(rect, used) for used in occupied):
                return rect
        return self._clamp_rect((ax + 26, ay + 14, ax + 26 + width, ay + 14 + height), image_width, image_height)

    @staticmethod
    def _clamp_rect(
        rect: tuple[int, int, int, int],
        image_width: int,
        image_height: int,
    ) -> tuple[int, int, int, int]:
        x0, y0, x1, y1 = rect
        width = x1 - x0
        height = y1 - y0
        x0 = max(6, min(x0, image_width - width - 6))
        y0 = max(6, min(y0, image_height - height - 6))
        return x0, y0, x0 + width, y0 + height

    @staticmethod
    def _rects_intersect(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
        margin = 6
        return not (a[2] + margin < b[0] or b[2] + margin < a[0] or a[3] + margin < b[1] or b[3] + margin < a[1])

    @staticmethod
    def _nearest_rect_point(anchor: tuple[int, int], rect: tuple[int, int, int, int]) -> tuple[int, int]:
        ax, ay = anchor
        x0, y0, x1, y1 = rect
        return max(x0, min(ax, x1)), max(y0, min(ay, y1))

    @staticmethod
    def _shortened_line(
        start: tuple[int, int],
        end: tuple[int, int],
        inset: int,
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.hypot(dx, dy)
        if length <= inset * 2:
            return start, end
        ux = dx / length
        uy = dy / length
        return (
            (round(start[0] + ux * inset), round(start[1] + uy * inset)),
            (round(end[0] - ux * inset), round(end[1] - uy * inset)),
        )

    def _wrap_cv2_text(
        self,
        cv2: Any,
        text: str,
        max_width: int,
        font: int,
        scale: float,
        thickness: int,
    ) -> list[str]:
        lines: list[str] = []
        current = ""
        for word in text.split():
            candidate = f"{current} {word}".strip()
            width = cv2.getTextSize(candidate, font, scale, thickness)[0][0]
            if current and width > max_width:
                lines.append(current)
                current = word
                if len(lines) >= self.style.banner_max_lines:
                    break
            else:
                current = candidate
        if current and len(lines) < self.style.banner_max_lines:
            lines.append(current)
        if not lines:
            lines = [text[:110]]
        if len(lines) == self.style.banner_max_lines and len(" ".join(lines)) < len(text):
            lines[-1] = lines[-1].rstrip(".") + "..."
        return lines

    @staticmethod
    def _wrap_plain_text(text: str, max_chars: int) -> list[str]:
        lines: list[str] = []
        current = ""
        for word in text.split():
            candidate = f"{current} {word}".strip()
            if current and len(candidate) > max_chars:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines or [text[:max_chars]]

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
