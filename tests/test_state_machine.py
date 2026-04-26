from __future__ import annotations

import pytest
from rich.console import Console

from circuit_sensei.agent import (
    AgentSession,
    CircuitSenseiAgent,
    ModelTurn,
    MockGeminiModelClient,
    SessionState,
    build_builtin_plan,
    breadboard_node,
    parse_state_transition,
    sanitize_user_facing_text,
    validate_and_repair_plan,
)
from circuit_sensei.tools import CircuitSenseiTools


def test_parse_state_transition_removes_block() -> None:
    clean, transition = parse_state_transition(
        'Inventory confirmed.\n%%STATE%%\n{"next_state":"PLAN","reason":"ready"}\n%%END%%'
    )

    assert clean == "Inventory confirmed."
    assert transition.next_state == SessionState.PLAN
    assert transition.reason == "ready"


def test_sanitize_user_facing_text_removes_leaked_controller_notes() -> None:
    leaked = (
        "* User Goal: Build a voltage divider with two 30 ohm resistors. "
        "* Current State: IDLE. "
        "* Inventory: Empty. "
        "* Goal: Move to INTAKE to gather the inventory of components available to the user. "
        "* IDLE -> INTAKE (if inventory is missing). "
        "* The user provided the goal but not the inventory. "
        "* I need to ask the user what components they have. "
        "* Acknowledge the goal. "
        "* Ask for the available inventory. "
        "* Transition to INTAKE state. "
        "Hello! I can help you build a voltage divider. What components do you have available?"
    )

    clean = sanitize_user_facing_text(leaked)

    assert clean == "Hello! I can help you build a voltage divider. What components do you have available?"
    assert "Current State" not in clean
    assert "Transition to" not in clean


def test_invalid_transition_is_rejected() -> None:
    session = AgentSession(current_state=SessionState.IDLE)

    with pytest.raises(ValueError):
        session.apply_transition(SessionState.TEST)


def test_emergency_response_starts_with_required_text(tmp_path) -> None:
    config = _config(tmp_path)
    agent = CircuitSenseiAgent(
        session=AgentSession(),
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=MockGeminiModelClient(),
    )

    response = agent.handle_user_message("The resistor is hot and I smell burning.")

    assert response.startswith("⚠️ DISCONNECT POWER NOW")


def test_mock_agent_progresses_from_idle_to_plan(tmp_path) -> None:
    config = _config(tmp_path)
    session = AgentSession()
    agent = CircuitSenseiAgent(
        session=session,
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=MockGeminiModelClient(),
    )

    response = agent.handle_user_message("Goal: blink an LED\nInventory: Arduino Uno, LED, 330 ohm resistor, jumpers")
    assert "goal and inventory" in response.lower() or "tell me" in response.lower()
    assert session.current_state == SessionState.INTAKE

    response = agent.handle_user_message("")
    assert "compact breadboard plan" in response.lower()
    assert session.current_state == SessionState.PLAN

    response = agent.handle_user_message("")
    assert "comprehensive plan" in response.lower()
    assert "current-limit resistor" not in response
    assert session.current_state == SessionState.INSTRUCT
    assert len(session.placement_plan) == 3


def test_agent_repairs_gemini_skipping_plan_state(tmp_path) -> None:
    config = _config(tmp_path)
    session = AgentSession(
        current_state=SessionState.INTAKE,
        circuit_goal="build a 2.5V voltage divider",
        inventory=["Arduino Uno", "two 10k resistors", "jumper wires"],
    )
    agent = CircuitSenseiAgent(
        session=session,
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=_OneShotClient('Ready.\n%%STATE%%\n{"next_state":"INSTRUCT","reason":"oops"}\n%%END%%'),
    )

    response = agent.handle_user_message("")

    assert "comprehensive plan" in response.lower()
    assert session.current_state == SessionState.PLAN
    assert len(session.placement_plan) == 3


def test_agent_repairs_idle_instruction_jump_with_plan_payload(tmp_path) -> None:
    config = _config(tmp_path)
    session = AgentSession()
    agent = CircuitSenseiAgent(
        session=session,
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=_OneShotClient(
            "Great! Insert the resistor into E10 and E12.\n"
            '%%STATE%%\n{"next_state":"INSTRUCT","reason":"jumped ahead"}\n%%END%%'
        ),
    )

    response = agent.handle_user_message(
        "Build a resistor and LED in series. I have a 330 resistor, jumpwires, and LED."
    )

    assert "comprehensive plan" in response.lower()
    assert "E10" not in response
    assert session.current_state == SessionState.PLAN
    assert len(session.placement_plan) == 3


def test_ready_from_prepared_plan_shows_one_instruction(tmp_path) -> None:
    config = _config(tmp_path)
    session = AgentSession(
        current_state=SessionState.PLAN,
        circuit_goal="blink an LED",
        inventory=["Arduino Uno", "LED", "330 ohm resistor"],
        placement_plan=build_builtin_plan("blink an LED"),
    )
    agent = CircuitSenseiAgent(
        session=session,
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=_OneShotClient("This should not be called."),
    )

    response = agent.handle_user_message("yes")

    assert "current-limit resistor" in response
    assert response.count("current-limit resistor") == 1
    assert session.current_state == SessionState.VERIFY


def test_agent_synthesizes_plan_when_gemini_omits_plan_json(tmp_path) -> None:
    config = _config(tmp_path)
    session = AgentSession(
        current_state=SessionState.PLAN,
        circuit_goal="build a 2.5V voltage divider",
        inventory=["Arduino Uno", "two 10k resistors", "jumper wires"],
    )
    agent = CircuitSenseiAgent(
        session=session,
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=_OneShotClient('Plan ready.\n%%STATE%%\n{"next_state":"INSTRUCT","reason":"ready"}\n%%END%%'),
    )

    response = agent.handle_user_message("")

    assert "comprehensive plan" in response.lower()
    assert session.current_state == SessionState.INSTRUCT
    assert session.placement_plan[0]["instruction"] == "With power disconnected, place R1 from A10 to A20."


def test_manual_confirm_advances_verify_step(tmp_path) -> None:
    config = _config(tmp_path)
    session = AgentSession(
        current_state=SessionState.VERIFY,
        circuit_goal="build a 2.5V voltage divider",
        inventory=["Arduino Uno", "two 10k resistors"],
        placement_plan=build_builtin_plan("build a 2.5V voltage divider"),
    )
    agent = CircuitSenseiAgent(
        session=session,
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=MockGeminiModelClient(),
    )

    response = agent.handle_user_message("I checked it")

    assert "Step 1 confirmed" in response
    assert session.current_state == SessionState.INSTRUCT
    assert session.current_step == 1
    assert session.verified_steps == [1]


def test_typed_text_during_verify_talks_without_advancing(tmp_path) -> None:
    config = _config(tmp_path)
    session = AgentSession(
        current_state=SessionState.VERIFY,
        circuit_goal="build a 2.5V voltage divider",
        inventory=["Arduino Uno", "two 10k resistors"],
        placement_plan=build_builtin_plan("build a 2.5V voltage divider"),
    )
    agent = CircuitSenseiAgent(
        session=session,
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=_OneShotClient(
            'Use the annotated holes A10 and A20 as the reference.\n%%STATE%%\n{"next_state":"VERIFY","reason":"answered"}\n%%END%%'
        ),
    )

    response = agent.handle_user_message("The image is blurry. What should I check?")

    assert "A10 and A20" in response
    assert session.current_state == SessionState.VERIFY
    assert session.current_step == 0
    assert session.verified_steps == []


def test_verify_failure_message_summarizes_json_analysis(tmp_path) -> None:
    config = _config(tmp_path)
    session = AgentSession(
        current_state=SessionState.VERIFY,
        circuit_goal="blink an LED",
        inventory=["Arduino Uno", "LED", "330 ohm resistor"],
        placement_plan=build_builtin_plan("blink an LED"),
    )
    agent = CircuitSenseiAgent(
        session=session,
        tools=_VerifyFailureTools(config, console=Console(file=None)),
        model_client=_OneShotClient("unused"),
    )

    response = agent.handle_user_message("ready")

    assert "camera check flagged an issue" in response.lower()
    assert "no led is visible on the breadboard" in response.lower()
    assert "```json" not in response
    assert '"passed": false' not in response.lower()
    assert session.current_state == SessionState.VERIFY


def test_test_state_runs_arduino_without_restarting_plan(tmp_path) -> None:
    config = _config(tmp_path)
    plan = build_builtin_plan("build a 2.5V voltage divider")
    session = AgentSession(
        current_state=SessionState.TEST,
        circuit_goal="build a 2.5V voltage divider",
        inventory=["Arduino Uno", "two 10k resistors"],
        placement_plan=plan,
        current_step=len(plan),
        verified_steps=[1, 2, 3],
    )
    agent = CircuitSenseiAgent(
        session=session,
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=_OneShotClient(
            'Bad replan.\n%%PLAN_JSON%%\n[{"step": 1, "instruction": "Restart"}]\n%%ENDPLAN_JSON%%\n%%STATE%%\n{"next_state":"INSTRUCT","reason":"oops"}\n%%END%%'
        ),
    )

    response = agent.handle_user_message("")

    assert "Arduino test result: PASS" in response
    assert session.current_state == SessionState.IDLE
    assert session.placement_plan == plan
    assert session.verified_steps == [1, 2, 3]


def test_breadboard_node_models_terminal_strips() -> None:
    assert breadboard_node("B", 15) == breadboard_node("C", 15)
    assert breadboard_node("B", 15) != breadboard_node("F", 15)


def test_plan_repair_moves_duplicate_hole_to_same_node() -> None:
    plan = [
        {
            "step": 1,
            "instruction": "Place R1 from B10 to B15.",
            "annotations": {
                "points": [
                    {"row": "B", "col": 10, "label": "R1 leg 1"},
                    {"row": "B", "col": 15, "label": "R1 leg 2"},
                ],
                "arrows": [
                    {
                        "from": {"row": "B", "col": 10},
                        "to": {"row": "B", "col": 15},
                        "label": "R1",
                    }
                ],
                "message": "Place R1 from B10 to B15.",
            },
        },
        {
            "step": 2,
            "instruction": "Place R2 from B15 to B20.",
            "annotations": {
                "points": [
                    {"row": "B", "col": 15, "label": "R2 leg 1"},
                    {"row": "B", "col": 20, "label": "R2 leg 2"},
                ],
                "arrows": [
                    {
                        "from": {"row": "B", "col": 15},
                        "to": {"row": "B", "col": 20},
                        "label": "R2",
                    }
                ],
                "message": "Place R2 from B15 to B20.",
            },
        },
    ]

    repaired, repairs = validate_and_repair_plan(plan)

    moved = repaired[1]["annotations"]["points"][0]
    arrow_from = repaired[1]["annotations"]["arrows"][0]["from"]
    assert moved == {"row": "C", "col": 15, "label": "R2 leg 1"}
    assert arrow_from == {"row": "C", "col": 15}
    assert "C15" in repaired[1]["instruction"]
    assert breadboard_node("B", 15) == breadboard_node("C", 15)
    assert repairs


def test_agent_reports_plan_hole_repairs(tmp_path) -> None:
    config = _config(tmp_path)
    plan_json = json_plan_with_duplicate_hole()
    session = AgentSession(
        current_state=SessionState.PLAN,
        circuit_goal="build a divider",
        inventory=["Arduino Uno", "two resistors"],
    )
    agent = CircuitSenseiAgent(
        session=session,
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=_OneShotClient(
            f"Plan ready.\n%%PLAN_JSON%%\n{plan_json}\n%%ENDPLAN_JSON%%\n%%STATE%%\n"
            '{"next_state":"INSTRUCT","reason":"ready"}\n%%END%%'
        ),
    )

    response = agent.handle_user_message("")

    assert "Adjusted for breadboard hole occupancy" in response
    assert session.placement_plan[1]["annotations"]["points"][0]["row"] == "C"


def test_setting_plan_clears_stale_annotation_image(tmp_path) -> None:
    config = _config(tmp_path)
    annotated_path = tmp_path / "sensei_annotated.jpg"
    annotated_path.write_bytes(b"old annotation")
    agent = CircuitSenseiAgent(
        session=AgentSession(circuit_goal="blink an LED", inventory=["Arduino Uno", "LED"]),
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=MockGeminiModelClient(),
    )

    agent._set_plan(build_builtin_plan("blink an LED"))

    assert not annotated_path.exists()


def test_advancing_step_clears_stale_annotation_image(tmp_path) -> None:
    config = _config(tmp_path)
    annotated_path = tmp_path / "sensei_annotated.jpg"
    annotated_path.write_bytes(b"step 1 annotation")
    plan = build_builtin_plan("blink an LED")
    session = AgentSession(
        current_state=SessionState.VERIFY,
        circuit_goal="blink an LED",
        inventory=["Arduino Uno", "LED"],
        placement_plan=plan,
    )
    session.add_history(
        "tool",
        CircuitSenseiTools.encode_tool_result("analyze_board", {"ok": True, "passed": True}),
        name="analyze_board",
    )
    agent = CircuitSenseiAgent(
        session=session,
        tools=CircuitSenseiTools(config, console=Console(file=None)),
        model_client=MockGeminiModelClient(),
    )

    agent._advance_step_if_verified(SessionState.VERIFY, SessionState.INSTRUCT)

    assert session.current_step == 1
    assert not annotated_path.exists()


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


class _OneShotClient:
    def __init__(self, text: str) -> None:
        self.text = text

    def generate(self, session: AgentSession, function_declarations):
        return ModelTurn(text=self.text)


class _VerifyFailureTools(CircuitSenseiTools):
    def execute(self, name: str, args=None):
        if name == "capture_frame":
            return {
                "ok": True,
                "path": self.frame_path,
                "message": "Webcam frame captured.",
            }
        if name == "analyze_board":
            return {
                "ok": True,
                "passed": False,
                "analysis": (
                    "```json\n"
                    "{\n"
                    '  "passed": false,\n'
                    '  "analysis": "No LED is visible on the breadboard in the provided image or any of its crops. Therefore, the requested placement of the LED with its anode in A15 and cathode in A20 cannot be verified.",\n'
                    '  "safety_concern": null\n'
                    "}\n"
                    "```"
                ),
                "image_path": self.frame_path,
            }
        return super().execute(name, args)


def json_plan_with_duplicate_hole() -> str:
    import json

    return json.dumps(
        [
            {
                "step": 1,
                "instruction": "Place R1 from B10 to B15.",
                "annotations": {
                    "points": [
                        {"row": "B", "col": 10, "label": "R1 leg 1"},
                        {"row": "B", "col": 15, "label": "R1 leg 2"},
                    ],
                    "message": "Place R1 from B10 to B15.",
                },
            },
            {
                "step": 2,
                "instruction": "Place R2 from B15 to B20.",
                "annotations": {
                    "points": [
                        {"row": "B", "col": 15, "label": "R2 leg 1"},
                        {"row": "B", "col": 20, "label": "R2 leg 2"},
                    ],
                    "message": "Place R2 from B15 to B20.",
                },
            },
        ]
    )
