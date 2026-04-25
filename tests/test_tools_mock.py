from __future__ import annotations

from rich.console import Console

from circuit_sensei.agent import AgentSession, CircuitSenseiAgent, MockGeminiModelClient
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
    assert annotated["points"] == 2
    assert annotated["arrows"] == 1
    assert annotated["warnings"] == []
    assert (tmp_path / "sensei_annotated.jpg").exists()


def test_reference_annotation_does_not_require_camera_capture(tmp_path) -> None:
    config = _config(tmp_path)
    config["hardware"]["mock_mode"] = False
    config["overlay"] = {"annotation_source": "reference"}
    tools = CircuitSenseiTools(config, console=Console(file=None))

    annotated = tools.annotate_frame(
        {
            "points": [{"row": "A", "col": 10, "label": "R1 leg"}],
            "message": "Place R1 leg at A10.",
        }
    )

    assert annotated["ok"] is True
    assert annotated["source"] == "reference"
    assert (tmp_path / "sensei_frame.jpg").exists()
    assert (tmp_path / "sensei_annotated.jpg").exists()


def test_annotation_flags_ambiguous_physical_guidance(tmp_path) -> None:
    tools = CircuitSenseiTools(_config(tmp_path), console=Console(file=None))

    tools.capture_frame()
    annotated = tools.annotate_frame(
        {
            "points": [
                {"row": "A", "col": 10, "label": "R1 leg"},
                {"row": "A", "col": 10, "label": "R2 leg"},
            ],
            "arrows": [
                {
                    "from": {"row": "E", "col": 12},
                    "to": {"row": "F", "col": 12},
                    "label": "center jumper",
                }
            ],
            "message": "Check duplicate target hole and center gap warning.",
        }
    )

    assert annotated["ok"] is True
    assert any("exact same hole A10" in warning for warning in annotated["warnings"])
    assert any("center gap" in warning for warning in annotated["warnings"])


def test_annotate_frame_supports_power_rail_points(tmp_path) -> None:
    tools = CircuitSenseiTools(_config(tmp_path), console=Console(file=None))

    annotated = tools.annotate_frame(
        {
            "points": [
                {"rail": "positive", "side": "left", "col": 3, "label": "+ rail"},
            ],
            "arrows": [
                {
                    "from": {"rail": "positive", "side": "left", "col": 1},
                    "to": {"rail": "positive", "side": "left", "col": 5},
                    "label": "power rail",
                }
            ],
            "message": "Connect 5V to the positive rail.",
        }
    )

    assert annotated["ok"] is True
    assert annotated["points"] == 1
    assert annotated["arrows"] == 1


def test_agent_derives_power_rail_annotations_when_holes_missing(tmp_path) -> None:
    tools = CircuitSenseiTools(_config(tmp_path), console=Console(file=None))
    agent = CircuitSenseiAgent(
        session=AgentSession(circuit_goal="power rail setup", inventory=["Arduino", "jumper wire"]),
        tools=tools,
        model_client=MockGeminiModelClient(),
    )

    step = {
        "step": 1,
        "instruction": (
            "Connect one end of a jumper wire to the Arduino's 5V pin and the other end "
            "to any hole in the breadboard's positive (+) power rail."
        ),
        "annotations": {
            "message": "Use the + rail.",
        },
    }

    annotations = agent._annotations_for_step(step)

    assert any(point.get("rail") == "positive" for point in annotations.get("points", []))
    assert len(annotations.get("arrows", [])) == 1

    rendered = tools.annotate_frame(annotations)
    assert rendered["ok"] is True
    assert rendered["points"] >= 1


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


def test_breadboard_geometry_models_terminal_strips() -> None:
    geometry = BreadboardGeometry(top_left=(10, 20), bottom_right=(630, 220), columns=63)

    assert geometry.node_key("A", 10) == ("top", 10)
    assert geometry.node_key("E", 10) == ("top", 10)
    assert geometry.node_key("F", 10) == ("bottom", 10)
    assert geometry.connected_rows("B") == ("A", "B", "C", "D", "E")


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
