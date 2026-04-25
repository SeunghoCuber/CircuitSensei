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
    parse_state_transition,
)
from circuit_sensei.tools import CircuitSenseiTools


def test_parse_state_transition_removes_block() -> None:
    clean, transition = parse_state_transition(
        'Inventory confirmed.\n%%STATE%%\n{"next_state":"PLAN","reason":"ready"}\n%%END%%'
    )

    assert clean == "Inventory confirmed."
    assert transition.next_state == SessionState.PLAN
    assert transition.reason == "ready"


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
    assert "placement plan" in response.lower()
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

    assert response == "Ready."
    assert session.current_state == SessionState.PLAN


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

    assert "placement plan" in response.lower()
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

    assert "Manual confirmation accepted for step 1" in response
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


class _OneShotClient:
    def __init__(self, text: str) -> None:
        self.text = text

    def generate(self, session: AgentSession, function_declarations):
        return ModelTurn(text=self.text)
