from __future__ import annotations

from circuit_sensei.agent import build_builtin_plan, generate_netlist


def test_generate_netlist_no_plan_returns_empty_state() -> None:
    text = generate_netlist("blink an LED", [], [])
    assert "Circuit-Sensei generated netlist" in text
    assert "No circuit plan available yet." in text


def test_generate_netlist_includes_goal_and_components() -> None:
    text = generate_netlist(
        "blink an LED",
        ["1 × LED", "1 × 330 ohm resistor"],
        build_builtin_plan("blink an LED"),
    )
    assert "Goal: blink an LED" in text
    assert "1 × LED" in text
    assert "1 × 330 ohm resistor" in text


def test_generate_netlist_resistor_uses_value_from_components() -> None:
    plan = build_builtin_plan("blink an LED")  # step 1 = resistor A10-A20
    text = generate_netlist("blink an LED", ["1 × 330 ohm resistor"], plan)
    # Resistor between top-bank column 10 and top-bank column 20.
    assert "R1 N_T10 N_T20 330" in text


def test_generate_netlist_emits_led_with_proper_nodes() -> None:
    plan = build_builtin_plan("blink an LED")  # step 2 = LED at E20-E25
    text = generate_netlist("blink an LED", ["1 × LED"], plan)
    assert "D1 N_T20 N_T25 LED" in text


def test_generate_netlist_includes_arduino_pin_endpoints() -> None:
    plan = build_builtin_plan("blink an LED")  # step 3 wires D9 and GND
    text = generate_netlist("blink an LED", [], plan)
    # Wires connect Arduino pin labels to breadboard nodes.
    assert "D9" in text
    assert "GND" in text


def test_generate_netlist_marks_test_steps_as_comments() -> None:
    plan = [
        {
            "step": 1,
            "kind": "build",
            "title": "Place R1",
            "instruction": "Place R1 from A10 to A20.",
            "annotations": {
                "arrows": [
                    {"from": {"row": "A", "col": 10}, "to": {"row": "A", "col": 20}, "label": "R1"}
                ],
            },
        },
        {
            "step": 2,
            "kind": "arduino_test",
            "title": "LED drive test",
            "test_type": "led",
        },
    ]
    text = generate_netlist("blink an LED", [], plan)
    assert "* Test step: LED drive test (led)" in text
    assert "R1 N_T10 N_T20" in text


def test_generate_netlist_handles_step_without_annotations() -> None:
    plan = [{"step": 1, "title": "Mystery step", "instruction": "Place something."}]
    text = generate_netlist("mystery", [], plan)
    assert "no inferable connections" in text


def test_generate_netlist_does_not_duplicate_repeat_edges() -> None:
    plan = [
        {
            "step": 1,
            "title": "Place R1",
            "instruction": "Place R1 from A10 to A20.",
            "annotations": {
                "arrows": [
                    {"from": {"row": "A", "col": 10}, "to": {"row": "A", "col": 20}, "label": "R1"},
                    {"from": {"row": "B", "col": 10}, "to": {"row": "C", "col": 20}, "label": "R1 dup"},
                ],
            },
        }
    ]
    text = generate_netlist("test", [], plan)
    # Both arrow endpoints normalize to the same top-bank nodes (T10 / T20),
    # so only one component line should be emitted.
    assert text.count("N_T10 N_T20") == 1
