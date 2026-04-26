from __future__ import annotations

import yaml
from rich.console import Console

from circuit_sensei.agent import AgentSession, CircuitSenseiAgent, MockGeminiModelClient
from circuit_sensei.hardware.overlay import BreadboardGeometry
from circuit_sensei.tools import CircuitSenseiTools, GeminiVisionAnalyzer, config_bool


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

    assert any(point.get("arduino_pin") == "5V" for point in annotations.get("points", []))
    assert any(point.get("rail") == "positive" for point in annotations.get("points", []))
    assert len(annotations.get("arrows", [])) == 1
    assert annotations["arrows"][0]["from"] == {"arduino_pin": "5V"}
    assert annotations["arrows"][0]["to"]["rail"] == "positive"

    rendered = tools.annotate_frame(annotations)
    assert rendered["ok"] is True
    assert rendered["points"] >= 2


def test_agent_derives_arduino_to_breadboard_wire_annotations(tmp_path) -> None:
    tools = CircuitSenseiTools(_config(tmp_path), console=Console(file=None))
    agent = CircuitSenseiAgent(
        session=AgentSession(circuit_goal="blink an LED", inventory=["Arduino", "jumper wire"]),
        tools=tools,
        model_client=MockGeminiModelClient(),
    )

    step = {
        "step": 1,
        "instruction": "Connect Arduino D9 to column 10 and Arduino GND to column 25.",
        "annotations": {"message": "Connect D9 and GND."},
    }

    annotations = agent._annotations_for_step(step)

    assert {"arduino_pin": "D9", "label": "D9"} in annotations["points"]
    assert {"arduino_pin": "GND", "label": "GND"} in annotations["points"]
    assert {"row": "J", "col": 10, "label": "J10"} in annotations["points"]
    assert {"row": "J", "col": 25, "label": "J25"} in annotations["points"]
    assert annotations["arrows"][0]["from"] == {"arduino_pin": "D9"}
    assert annotations["arrows"][0]["to"] == {"row": "J", "col": 10}
    assert annotations["arrows"][1]["from"] == {"arduino_pin": "GND"}
    assert annotations["arrows"][1]["to"] == {"row": "J", "col": 25}

    rendered = tools.annotate_frame(annotations)
    assert rendered["ok"] is True


def test_mock_arduino_voltage_divider(tmp_path) -> None:
    tools = CircuitSenseiTools(_config(tmp_path), console=Console(file=None))

    connected = tools.arduino_connect("/dev/mock")
    result = tools.run_test_script("voltage_divider", {"expected_voltage": 2.5, "tolerance": 0.2})

    assert connected["ok"] is True
    assert result["status"] == "ok"
    assert result["passed"] is True


def test_vision_verdict_requires_explicit_passed_boolean() -> None:
    assert GeminiVisionAnalyzer._extract_passed_verdict('{"passed": true, "analysis": "OK"}') is True
    assert GeminiVisionAnalyzer._extract_passed_verdict("```json\n{\"passed\": false}\n```") is False
    assert GeminiVisionAnalyzer._extract_passed_verdict("Looks okay from here.") is None


def test_mock_mode_string_false_disables_mocking(tmp_path) -> None:
    config = _config(tmp_path)
    config["hardware"]["mock_mode"] = "false"

    tools = CircuitSenseiTools(config, console=Console(file=None))

    assert config_bool("0", default=True) is False
    assert config_bool("no", default=True) is False
    assert tools.mock_mode is False
    assert tools.vision.mock_mode is False


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


def test_production_arduino_digital_header_calibration() -> None:
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    pins = BreadboardGeometry.from_config(config).arduino_pins

    assert pins["SDA"] == (913, 510)
    assert pins["SCL"] == (913, 555)
    assert pins["AREF"] == (913, 600)
    assert pins["D13"] == (913, 689)
    assert pins["D11"] == (913, 778)
    assert pins["D10"] == (913, 823)
    assert pins["D9"] == (913, 868)
    assert pins["D8"] == (913, 912)


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
        "arduino": {
            "pins": {
                "5V": [20, 80],
                "GND": [20, 100],
                "D9": [20, 120],
                "A0": [20, 140],
            }
        },
    }
