from __future__ import annotations

from rich.console import Console

from circuit_sensei.hardware.overlay import BreadboardGeometry
from circuit_sensei.tools import CircuitSenseiTools


def test_mock_capture_and_annotate(tmp_path) -> None:
    tools = CircuitSenseiTools(_config(tmp_path), console=Console(file=None))

    capture = tools.capture_frame()
    assert capture["ok"] is True
    assert (tmp_path / "sensei_frame.jpg").exists()

    annotation = {
        "points": [
            {"row": "A", "col": 10, "label": "resistor leg 1"},
            {"row": "A", "col": 20, "label": "resistor leg 2"},
        ],
        "arrows": [
            {"from": {"row": "A", "col": 10}, "to": {"row": "A", "col": 20}, "label": "place 1k resistor"}
        ],
        "message": "Place the 1k resistor between A10 and A20.",
    }
    annotated = tools.annotate_frame(annotation)

    assert annotated["ok"] is True
    assert (tmp_path / "sensei_annotated.jpg").exists()


def test_mock_arduino_voltage_divider(tmp_path) -> None:
    tools = CircuitSenseiTools(_config(tmp_path), console=Console(file=None))

    connected = tools.arduino_connect("/dev/mock")
    result = tools.run_test_script("voltage_divider", {"expected_voltage": 2.5, "tolerance": 0.2})

    assert connected["ok"] is True
    assert result["status"] == "ok"
    assert result["passed"] is True


def test_breadboard_geometry_maps_edges() -> None:
    geometry = BreadboardGeometry(top_left=(10, 20), bottom_right=(630, 220), columns=63)

    assert geometry.hole_to_pixel("A", 1) == (10, 20)
    assert geometry.hole_to_pixel("J", 63) == (630, 220)


def _config(tmp_path):
    return {
        "gemini": {"model": "gemini-2.5-flash", "vision_model": "gemini-2.5-flash", "retries": 1},
        "hardware": {"mock_mode": True, "camera_index": 0, "serial_port": "/dev/mock", "baud_rate": 115200},
        "paths": {
            "frame_path": str(tmp_path / "sensei_frame.jpg"),
            "annotated_path": str(tmp_path / "sensei_annotated.jpg"),
        },
        "breadboard": {
            "image_size": [640, 360],
            "top_left": [50, 50],
            "bottom_right": [590, 310],
            "rows": list("ABCDEFGHIJ"),
            "columns": 63,
        },
    }
