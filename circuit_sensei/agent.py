"""Direct Gemini agent loop and state machine for Circuit-Sensei."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from circuit_sensei.prompts.system_prompt import SYSTEM_PROMPT
from circuit_sensei.tools import CircuitSenseiTools, ToolCall, config_bool


class SessionState(str, Enum):
    """Finite states for the Circuit-Sensei build workflow."""

    IDLE = "IDLE"
    INTAKE = "INTAKE"
    PLAN = "PLAN"
    INSTRUCT = "INSTRUCT"
    VERIFY = "VERIFY"
    VERIFY_COMPLETE = "VERIFY_COMPLETE"
    TEST = "TEST"


ALLOWED_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.IDLE: {SessionState.INTAKE, SessionState.PLAN},
    SessionState.INTAKE: {SessionState.PLAN, SessionState.INTAKE},
    SessionState.PLAN: {SessionState.INSTRUCT, SessionState.PLAN},
    SessionState.INSTRUCT: {SessionState.VERIFY, SessionState.IDLE},
    SessionState.VERIFY: {SessionState.INSTRUCT, SessionState.VERIFY, SessionState.VERIFY_COMPLETE},
    SessionState.VERIFY_COMPLETE: {SessionState.TEST, SessionState.IDLE},
    SessionState.TEST: {SessionState.IDLE, SessionState.INSTRUCT},
}


@dataclass
class AgentSession:
    """Mutable Circuit-Sensei session state shared across agent turns."""

    current_state: SessionState = SessionState.IDLE
    circuit_goal: str = ""
    inventory: list[str] = field(default_factory=list)
    placement_plan: list[dict[str, Any]] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    current_step: int = 0
    verified_steps: list[int] = field(default_factory=list)
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    breadboard_geometry: dict[str, Any] = field(default_factory=dict)
    arduino_connected: bool = False
    arduino_port: str | None = None
    plan_repairs: list[str] = field(default_factory=list)

    def add_history(self, role: str, content: Any, name: str | None = None) -> None:
        """Append an item to conversation history."""

        entry = {"role": role, "content": content}
        if name:
            entry["name"] = name
        self.conversation_history.append(entry)

    def apply_transition(self, next_state: SessionState) -> None:
        """Validate and apply a state transition."""

        allowed = ALLOWED_TRANSITIONS[self.current_state]
        if next_state not in allowed:
            raise ValueError(f"Invalid transition {self.current_state.value} -> {next_state.value}")
        self.current_state = next_state

    def snapshot(self) -> dict[str, Any]:
        """Return a compact JSON-serializable state snapshot for the model."""

        return {
            "current_state": self.current_state.value,
            "circuit_goal": self.circuit_goal,
            "inventory": self.inventory,
            "placement_plan": self.placement_plan,
            "components": self.components,
            "current_step": self.current_step + 1 if self.placement_plan else 0,
            "verified_steps": self.verified_steps,
            "breadboard_geometry": self.breadboard_geometry,
            "arduino_connected": self.arduino_connected,
            "arduino_port": self.arduino_port,
            "plan_repairs": self.plan_repairs,
        }


@dataclass(frozen=True)
class StateTransition:
    """Parsed model state transition block."""

    next_state: SessionState
    reason: str


@dataclass(frozen=True)
class ModelTurn:
    """One Gemini response, either text or requested tool calls."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class ModelClient(Protocol):
    """Minimal model client protocol used by the agent loop."""

    def generate(self, session: AgentSession, function_declarations: list[dict[str, Any]]) -> ModelTurn:
        """Generate a model turn from current session state."""


STATE_BLOCK_RE = re.compile(r"%%STATE%%\s*(\{.*?\})\s*%%END%%", re.DOTALL)
PLAN_BLOCK_RE = re.compile(r"%%PLAN_JSON%%\s*(\[.*?\])\s*%%ENDPLAN_JSON%%", re.DOTALL)
COMPONENTS_BLOCK_RE = re.compile(r"%%COMPONENTS_JSON%%\s*(\[.*?\])\s*%%ENDCOMPONENTS_JSON%%", re.DOTALL)
HOLE_REF_RE = re.compile(r"\b([A-Ja-j])\s*([1-9][0-9]?)\b")
COLUMN_REF_RE = re.compile(r"\bcol(?:umn)?s?\.?\s*([1-9][0-9]?)\b", re.IGNORECASE)
ARDUINO_PIN_RE = re.compile(r"\b(?:a|d)(?:0|[1-9][0-3]?)\b", re.IGNORECASE)
ARDUINO_ENDPOINT_RE = re.compile(
    r"\b(?:D(?:0|[1-9]|1[0-3])|A[0-5]|AREF|IOREF|RESET|VIN|GND|GROUND|3V3|3\.3\s*V|5\s*V|RX|TX)\b",
    re.IGNORECASE,
)

ARDUINO_PIN_ALIASES = {
    "3.3V": "3V3",
    "3V3": "3V3",
    "5V": "5V",
    "GND": "GND",
    "GROUND": "GND",
    "RX": "D0",
    "TX": "D1",
}

WIRE_HINT_TOKENS = (
    "wire",
    "jumper",
    "lead",
    "connect",
    "connection",
    "gnd",
    "ground",
    "5v",
    "3v3",
    "vcc",
    "vin",
    "rail",
    "signal",
    "to arduino",
)

COMPONENT_HINT_TOKENS = (
    "resistor",
    "led",
    "diode",
    "capacitor",
    "transistor",
    "sensor",
    "button",
    "potentiometer",
    "ic",
    "chip",
    "module",
)


DETERMINISTIC_FALLBACKS: dict[SessionState, SessionState] = {
    SessionState.IDLE: SessionState.INTAKE,
    SessionState.INTAKE: SessionState.INTAKE,
    SessionState.PLAN: SessionState.PLAN,
    SessionState.INSTRUCT: SessionState.VERIFY,
    SessionState.VERIFY: SessionState.VERIFY,
    SessionState.VERIFY_COMPLETE: SessionState.TEST,
    SessionState.TEST: SessionState.IDLE,
}

TOP_BANK_ROWS = tuple("ABCDE")
BOTTOM_BANK_ROWS = tuple("FGHIJ")
ALL_BREADBOARD_ROWS = TOP_BANK_ROWS + BOTTOM_BANK_ROWS


def build_builtin_plan(circuit_goal: str) -> list[dict[str, Any]]:
    """Return a safe built-in plan when Gemini omits structured plan JSON."""

    goal = circuit_goal.lower()
    if "divider" in goal:
        return [
            {
                "step": 1,
                "title": "Place R1",
                "instruction": "With power disconnected, place R1 from A10 to A20.",
                "verification": "Verify a resistor bridges A10 and A20.",
                "annotations": {
                    "points": [
                        {"row": "A", "col": 10, "label": "R1 leg 1"},
                        {"row": "A", "col": 20, "label": "R1 leg 2"},
                    ],
                    "arrows": [
                        {
                            "from": {"row": "A", "col": 10},
                            "to": {"row": "A", "col": 20},
                            "label": "R1",
                        }
                    ],
                    "message": "Place R1 between A10 and A20.",
                },
            },
            {
                "step": 2,
                "title": "Place R2",
                "instruction": "Place R2 from B20 to B30, using B20 as the same midpoint node as R1's A20 leg.",
                "verification": "Verify R2 bridges B20 and B30. B20 is electrically common with A20, but it is a separate physical hole.",
                "annotations": {
                    "points": [
                        {"row": "B", "col": 20, "label": "R2 leg 1"},
                        {"row": "B", "col": 30, "label": "R2 leg 2"},
                    ],
                    "arrows": [
                        {
                            "from": {"row": "B", "col": 20},
                            "to": {"row": "B", "col": 30},
                            "label": "R2",
                        }
                    ],
                    "message": "Place R2 between B20 and B30.",
                },
            },
            {
                "step": 3,
                "title": "Wire Arduino leads",
                "instruction": "With Arduino outputs still inactive, connect A0 to C20, D9 to B10, and GND to C30.",
                "verification": "Verify A0 reaches C20, D9 reaches B10, and GND reaches C30. These use free holes on the same nodes as the divider.",
                "annotations": {
                    "points": [
                        {"arduino_pin": "A0", "label": "A0"},
                        {"row": "C", "col": 20, "label": "A0 sense"},
                        {"arduino_pin": "D9", "label": "D9"},
                        {"row": "B", "col": 10, "label": "D9 test source"},
                        {"arduino_pin": "GND", "label": "GND"},
                        {"row": "C", "col": 30, "label": "GND"},
                    ],
                    "arrows": [
                        {
                            "from": {"arduino_pin": "A0"},
                            "to": {"row": "C", "col": 20},
                            "label": "A0 jumper",
                        },
                        {
                            "from": {"arduino_pin": "D9"},
                            "to": {"row": "B", "col": 10},
                            "label": "D9 jumper",
                        },
                        {
                            "from": {"arduino_pin": "GND"},
                            "to": {"row": "C", "col": 30},
                            "label": "GND jumper",
                        },
                    ],
                    "message": "Wire Arduino test leads: A0 to C20, D9 to B10, GND to C30.",
                },
            },
        ]

    return [
        {
            "step": 1,
            "title": "Place resistor",
            "instruction": "With power disconnected, place the current-limit resistor from A10 to A20.",
            "verification": "Verify the resistor bridges A10 and A20.",
            "annotations": {
                "points": [
                    {"row": "A", "col": 10, "label": "resistor leg 1"},
                    {"row": "A", "col": 20, "label": "resistor leg 2"},
                ],
                "arrows": [
                    {
                        "from": {"row": "A", "col": 10},
                        "to": {"row": "A", "col": 20},
                        "label": "220-1k resistor",
                    }
                ],
                "message": "Place the resistor between A10 and A20.",
            },
        },
        {
            "step": 2,
            "title": "Place LED",
            "instruction": "Place the LED anode at E20 and cathode at E25.",
            "verification": "Verify LED polarity: longer/anode leg at E20, shorter/cathode leg at E25.",
            "annotations": {
                "points": [
                    {"row": "E", "col": 20, "label": "LED anode"},
                    {"row": "E", "col": 25, "label": "LED cathode"},
                ],
                "arrows": [
                    {
                        "from": {"row": "E", "col": 20},
                        "to": {"row": "E", "col": 25},
                        "label": "LED",
                    }
                ],
                "message": "Place LED from E20 anode to E25 cathode.",
            },
        },
        {
            "step": 3,
            "title": "Wire Arduino",
            "instruction": "With Arduino outputs still inactive, connect D9 to column 10 and GND to column 25.",
            "verification": "Verify D9 reaches column 10 and GND reaches column 25; no power has been applied yet.",
            "annotations": {
                "points": [
                    {"arduino_pin": "D9", "label": "D9"},
                    {"row": "J", "col": 10, "label": "D9"},
                    {"arduino_pin": "GND", "label": "GND"},
                    {"row": "J", "col": 25, "label": "GND"},
                ],
                "arrows": [
                    {
                        "from": {"arduino_pin": "D9"},
                        "to": {"row": "J", "col": 10},
                        "label": "D9 jumper",
                    },
                    {
                        "from": {"arduino_pin": "GND"},
                        "to": {"row": "J", "col": 25},
                        "label": "GND jumper",
                    },
                ],
                "message": "Connect test leads: D9 to column 10, GND to column 25.",
            },
        },
    ]


def build_builtin_components(circuit_goal: str) -> list[str]:
    """Return a conservative parts list when Gemini omits components JSON."""

    goal = circuit_goal.lower()
    if "divider" in goal:
        return ["2 × resistor (equal value, e.g. 10 kΩ)", "3 × jumper wire"]
    return ["1 × LED", "1 × 330 Ω resistor", "3 × jumper wire"]


def summarize_builtin_plan(plan: list[dict[str, Any]], goal: str) -> str:
    """Create a concise user-facing summary for a built-in placement plan."""

    if "divider" in goal.lower():
        calc = "For equal resistors, Vout = Vin * R2 / (R1 + R2) = 5 V * 1/2 = 2.5 V."
    else:
        calc = "For an LED on 5 V, R = (5 V - about 2 V) / 5-10 mA, so 330 ohm to 1 kOhm is a gentle prototype range."
    steps = "\n".join(f"{item['step']}. {item['instruction']}" for item in plan)
    return f"{calc}\n\nPlacement plan:\n{steps}"


def summarize_plan_ready(goal: str) -> str:
    """Return the compact chat message shown after a plan is available."""

    label = goal.strip()
    if label:
        label = re.sub(r"\bi\s+have\b.*$", "", label, flags=re.IGNORECASE).strip(" .")
        label = re.sub(r"^(?:goal\s*:\s*)?(?:build|make)\s+", "", label, flags=re.IGNORECASE).strip(" .")
    if not label or len(label) > 80:
        label = "this circuit"
    elif not re.match(r"^(?:a|an|the)\s+", label, flags=re.IGNORECASE) and "circuit" not in label.lower():
        label = "this circuit"
    return (
        f"Okay, I've produced a comprehensive plan to build {label}. "
        "Let me know when you're ready to get started."
    )


def breadboard_node(row: str, col: int) -> tuple[str, int]:
    """Return the electrical node for a breadboard hole."""

    normalized = row.upper().strip()
    if normalized in TOP_BANK_ROWS:
        return "top", col
    if normalized in BOTTOM_BANK_ROWS:
        return "bottom", col
    return normalized, col


def equivalent_holes(row: str, col: int) -> list[tuple[str, int]]:
    """Return other holes electrically common with ``row``/``col``."""

    normalized = row.upper().strip()
    if normalized in TOP_BANK_ROWS:
        rows = _rotated_rows(TOP_BANK_ROWS, normalized)
    elif normalized in BOTTOM_BANK_ROWS:
        rows = _rotated_rows(BOTTOM_BANK_ROWS, normalized)
    else:
        rows = (normalized,)
    return [(candidate, col) for candidate in rows]


def _rotated_rows(rows: tuple[str, ...], first: str) -> tuple[str, ...]:
    index = rows.index(first)
    return rows[index:] + rows[:index]


def validate_and_repair_plan(plan: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Repair exact-hole reuse while preserving breadboard electrical nodes."""

    import copy

    repaired = copy.deepcopy(plan)
    occupied: dict[tuple[str, int], str] = {}
    repairs: list[str] = []

    for step in repaired:
        replacements: dict[tuple[str, int], tuple[str, int]] = {}
        for point in _iter_unique_hole_dicts(step):
            location = _hole_from_mapping(point)
            if location is None:
                continue
            row, col = location
            label = str(point.get("label", step.get("instruction", "connection")))
            key = (row, col)

            if key not in occupied:
                occupied[key] = label
                continue

            replacement = _first_free_equivalent(row, col, occupied)
            if replacement is None:
                repairs.append(
                    f"Could not repair duplicate hole {row}{col}; all holes on node {breadboard_node(row, col)} are occupied."
                )
                continue

            new_row, new_col = replacement
            point["row"] = new_row
            point["col"] = new_col
            occupied[replacement] = label
            replacements[key] = replacement
            repairs.append(
                f"Moved {label} from occupied hole {row}{col} to electrically equivalent hole {new_row}{new_col}."
            )

        if replacements:
            _apply_location_replacements(step, replacements)
            _apply_text_replacements(step, replacements)

    return repaired, repairs


def _iter_unique_hole_dicts(step: dict[str, Any]) -> list[dict[str, Any]]:
    """Return unique mutable row/col dictionaries from one plan step."""

    seen: set[int] = set()
    point_locations: set[tuple[str, int]] = set()
    holes: list[dict[str, Any]] = []
    annotations = step.get("annotations", {})
    if not isinstance(annotations, dict):
        return holes

    for point in annotations.get("points", []):
        if isinstance(point, dict) and id(point) not in seen:
            seen.add(id(point))
            holes.append(point)
            location = _hole_from_mapping(point)
            if location is not None:
                point_locations.add(location)

    for arrow in annotations.get("arrows", []):
        if not isinstance(arrow, dict):
            continue
        for key in ("from", "to"):
            endpoint = arrow.get(key)
            if isinstance(endpoint, dict) and id(endpoint) not in seen:
                location = _hole_from_mapping(endpoint)
                if location in point_locations:
                    continue
                seen.add(id(endpoint))
                holes.append(endpoint)
    return holes


def _hole_from_mapping(mapping: dict[str, Any]) -> tuple[str, int] | None:
    try:
        row = str(mapping["row"]).strip().upper()
        col = int(mapping["col"])
    except (KeyError, TypeError, ValueError):
        return None
    if row not in ALL_BREADBOARD_ROWS:
        return None
    return row, col


def _first_free_equivalent(
    row: str,
    col: int,
    occupied: dict[tuple[str, int], str],
) -> tuple[str, int] | None:
    for candidate in equivalent_holes(row, col):
        if candidate not in occupied:
            return candidate
    return None


def _apply_text_replacements(
    step: dict[str, Any],
    replacements: dict[tuple[str, int], tuple[str, int]],
) -> None:
    fields = ["instruction", "verification"]
    annotations = step.get("annotations")
    if isinstance(annotations, dict):
        fields.append("annotations.message")

    for field in fields:
        if field == "annotations.message":
            value = annotations.get("message") if isinstance(annotations, dict) else None
            if isinstance(value, str):
                annotations["message"] = _replace_locations(value, replacements)
            continue
        value = step.get(field)
        if isinstance(value, str):
            step[field] = _replace_locations(value, replacements)

    if isinstance(annotations, dict):
        for arrow in annotations.get("arrows", []):
            if isinstance(arrow, dict) and isinstance(arrow.get("label"), str):
                arrow["label"] = _replace_locations(arrow["label"], replacements)
        for point in annotations.get("points", []):
            if isinstance(point, dict) and isinstance(point.get("label"), str):
                point["label"] = _replace_locations(point["label"], replacements)


def _replace_locations(text: str, replacements: dict[tuple[str, int], tuple[str, int]]) -> str:
    updated = text
    for old, new in replacements.items():
        old_label = f"{old[0]}{old[1]}"
        new_label = f"{new[0]}{new[1]}"
        updated = re.sub(rf"\b{re.escape(old_label)}\b", new_label, updated)
    return updated


def _apply_location_replacements(
    step: dict[str, Any],
    replacements: dict[tuple[str, int], tuple[str, int]],
) -> None:
    annotations = step.get("annotations", {})
    if not isinstance(annotations, dict):
        return
    for mapping in _all_hole_dicts(annotations):
        location = _hole_from_mapping(mapping)
        if location in replacements:
            new_row, new_col = replacements[location]
            mapping["row"] = new_row
            mapping["col"] = new_col


def _all_hole_dicts(annotations: dict[str, Any]) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    for point in annotations.get("points", []):
        if isinstance(point, dict):
            mappings.append(point)
    for arrow in annotations.get("arrows", []):
        if not isinstance(arrow, dict):
            continue
        for key in ("from", "to"):
            endpoint = arrow.get(key)
            if isinstance(endpoint, dict):
                mappings.append(endpoint)
    return mappings


class GeminiModelClient:
    """Google Gemini Python SDK client with function-calling support and retries."""

    def __init__(self, model: str, retries: int = 3) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing. Set it or run with mock mode enabled.")

        from google import genai  # type: ignore[import-not-found]

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.retries = retries

    def generate(self, session: AgentSession, function_declarations: list[dict[str, Any]]) -> ModelTurn:
        """Call Gemini and extract either function calls or text."""

        from google.genai import types  # type: ignore[import-not-found]

        prompt = self._build_prompt(session)
        tools: list[dict[str, Any]] = []
        if function_declarations:
            tools = [{"function_declarations": function_declarations}]

        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=tools,
                    ),
                )
                return self._parse_response(response)
            except Exception as exc:  # pragma: no cover - external service
                last_error = exc
                time.sleep(0.75 * (2**attempt))
        raise RuntimeError(f"Gemini call failed after {self.retries} attempts: {last_error}")

    def _build_prompt(self, session: AgentSession) -> str:
        history = session.conversation_history[-16:]
        return (
            "Current Circuit-Sensei session JSON:\n"
            f"{json.dumps(session.snapshot(), indent=2, sort_keys=True)}\n\n"
            "Recent conversation/tool history JSON:\n"
            f"{json.dumps(history, indent=2, sort_keys=True)}\n\n"
            "Important controller contract:\n"
            "- Do not skip allowed state transitions.\n"
            "- In IDLE, transition to INTAKE unless the user already supplied both goal and inventory; then transition to PLAN.\n"
            "- In INTAKE, transition only to INTAKE or PLAN.\n"
            "- In PLAN, include %%PLAN_JSON%% with step annotations before moving to INSTRUCT.\n"
            "  Each plan step must include a 'title' field: a 2-5 word concise label (e.g. 'Place R1 resistor').\n"
            "  Also include %%COMPONENTS_JSON%% with a flat string list of required components (e.g. ['1 × LED', '2 × 330 Ω resistor']).\n"
            "- Plan with breadboard topology: A-E in the same column are electrically connected; F-J in the same column are electrically connected; E/F are separated by the center gap.\n"
            "- Never put two physical leads into the exact same hole. Use an electrically equivalent free hole on the same node instead.\n"
            "- In INSTRUCT, give exactly one concise physical step; the host app handles camera annotation.\n"
            "  End instruction messages with: 'When you've placed it, say **ready** to check with the camera — or **looks good** to confirm yourself.'\n"
            "- In VERIFY, wait for vision tool results before advancing.\n"
            "  On failure tell the user: 'Say **retry** to check again, or **looks good** to confirm manually.' Never mention /next or /confirm.\n\n"
            "Return either tool calls or a normal user-facing response with the required state block."
        )

    def _parse_response(self, response: Any) -> ModelTurn:
        parts = []
        tool_calls: list[ToolCall] = []
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            content = getattr(candidates[0], "content", None)
            parts = list(getattr(content, "parts", []) or [])

        text_parts: list[str] = []
        for part in parts:
            function_call = getattr(part, "function_call", None)
            if function_call:
                args = dict(getattr(function_call, "args", {}) or {})
                tool_calls.append(ToolCall(name=str(function_call.name), args=args))
            text = getattr(part, "text", None)
            if text:
                text_parts.append(str(text))

        if tool_calls:
            return ModelTurn(tool_calls=tool_calls)
        text = "\n".join(text_parts).strip() or (getattr(response, "text", "") or "")
        return ModelTurn(text=text.strip())


class MockGeminiModelClient:
    """Deterministic local model substitute for hackathon development."""

    def __init__(self) -> None:
        self._instruct_stage: dict[int, str] = {}
        self._verify_stage: dict[int, str] = {}
        self._test_stage = ""

    def generate(self, session: AgentSession, function_declarations: list[dict[str, Any]]) -> ModelTurn:
        state = session.current_state
        if state == SessionState.IDLE:
            return ModelTurn(text=self._with_state("Tell me the circuit goal and available components.", "INTAKE", "new session"))
        if state == SessionState.INTAKE:
            if session.circuit_goal and session.inventory:
                return ModelTurn(
                    text=self._with_state(
                        "Great. I have the goal and inventory. I will derive a compact breadboard plan next.",
                        "PLAN",
                        "goal and inventory captured",
                    )
                )
            return ModelTurn(
                text=self._with_state(
                    "I still need both the circuit goal and the component inventory before planning.",
                    "INTAKE",
                    "intake incomplete",
                )
            )
        if state == SessionState.PLAN:
            plan = self._mock_plan(session)
            plan_block = "%%PLAN_JSON%%\n" + json.dumps(plan, indent=2) + "\n%%ENDPLAN_JSON%%"
            components = self._mock_components(session)
            components_block = "%%COMPONENTS_JSON%%\n" + json.dumps(components) + "\n%%ENDCOMPONENTS_JSON%%"
            body = self._plan_summary(plan, session.circuit_goal)
            return ModelTurn(text=f"{body}\n\n{plan_block}\n{components_block}\n{self._state_json('INSTRUCT', 'placement plan ready')}")
        if state == SessionState.INSTRUCT:
            return self._mock_instruct(session)
        if state == SessionState.VERIFY:
            return self._mock_verify(session)
        if state == SessionState.VERIFY_COMPLETE:
            return ModelTurn(
                text=self._with_state(
                    "Visual safety verification passed. Keep the Arduino connected by USB and leave outputs inactive until the test command runs.",
                    "TEST",
                    "ready for serial testing",
                )
            )
        if state == SessionState.TEST:
            return self._mock_test(session)
        return ModelTurn(text=self._with_state("Ready.", "INTAKE", "fallback"))

    def _mock_instruct(self, session: AgentSession) -> ModelTurn:
        step = self._current_plan_step(session)
        stage = self._instruct_stage.get(session.current_step)
        annotations = dict(step.get("annotations", {}))
        annotations.setdefault("step", step.get("step", session.current_step + 1))
        if not stage:
            self._instruct_stage[session.current_step] = "annotated"
            return ModelTurn(tool_calls=[ToolCall("annotate_frame", {"annotations": annotations})])
        if stage == "annotated":
            self._instruct_stage[session.current_step] = "shown"
            return ModelTurn(tool_calls=[ToolCall("show_annotated_frame", {})])
        instruction = str(step.get("instruction", "Place the next component as annotated."))
        return ModelTurn(text=self._with_state(instruction, "VERIFY", "instruction shown"))

    def _mock_verify(self, session: AgentSession) -> ModelTurn:
        step = self._current_plan_step(session)
        stage = self._verify_stage.get(session.current_step)
        if not stage:
            self._verify_stage[session.current_step] = "captured"
            return ModelTurn(tool_calls=[ToolCall("capture_frame", {})])
        if stage == "captured":
            self._verify_stage[session.current_step] = "analyzed"
            instruction = str(step.get("verification", step.get("instruction", "")))
            return ModelTurn(tool_calls=[ToolCall("analyze_board", {"instruction": instruction})])
        if session.current_step + 1 >= len(session.placement_plan):
            return ModelTurn(text=self._with_state("That placement passes the visual check. All build steps are visually verified.", "VERIFY_COMPLETE", "all steps verified"))
        return ModelTurn(text=self._with_state("That placement passes the visual check. Move to the next annotated step.", "INSTRUCT", "step verified"))

    def _mock_test(self, session: AgentSession) -> ModelTurn:
        if self._test_stage == "":
            self._test_stage = "connected"
            return ModelTurn(tool_calls=[ToolCall("arduino_connect", {"port": session.arduino_port})])
        if self._test_stage == "connected":
            self._test_stage = "tested"
            test_type, expected = self._mock_test_spec(session.circuit_goal)
            return ModelTurn(tool_calls=[ToolCall("run_test_script", {"test_type": test_type, "expected_values": expected})])
        return ModelTurn(
            text=self._with_state(
                "Mock Arduino measurements are in tolerance, so the prototype circuit is reported as working.",
                "IDLE",
                "test complete",
            )
        )

    def _current_plan_step(self, session: AgentSession) -> dict[str, Any]:
        if not session.placement_plan:
            return {
                "step": 1,
                "instruction": "Place the component as annotated.",
                "annotations": {"message": "Place the component."},
            }
        return session.placement_plan[min(session.current_step, len(session.placement_plan) - 1)]

    def _mock_plan(self, session: AgentSession) -> list[dict[str, Any]]:
        return build_builtin_plan(session.circuit_goal)

    def _mock_test_spec(self, goal: str) -> tuple[str, dict[str, Any]]:
        if "divider" in goal.lower():
            return "voltage_divider", {"expected_voltage": 2.5, "tolerance": 0.2}
        return "led", {"sense_pin": "A0"}

    def _mock_components(self, session: AgentSession) -> list[str]:
        return build_builtin_components(session.circuit_goal)

    def _plan_summary(self, plan: list[dict[str, Any]], goal: str) -> str:
        return summarize_builtin_plan(plan, goal)

    def _with_state(self, body: str, next_state: str, reason: str) -> str:
        return f"{body}\n\n{self._state_json(next_state, reason)}"

    def _state_json(self, next_state: str, reason: str) -> str:
        return "%%STATE%%\n" + json.dumps({"next_state": next_state, "reason": reason}) + "\n%%END%%"


class CircuitSenseiAgent:
    """Run the direct Gemini/tool/state-machine loop."""

    def __init__(
        self,
        session: AgentSession,
        tools: CircuitSenseiTools,
        model_client: ModelClient,
        max_tool_rounds: int = 6,
    ) -> None:
        self.session = session
        self.tools = tools
        self.model_client = model_client
        self.max_tool_rounds = max_tool_rounds

    def handle_user_message(self, user_text: str) -> str:
        """Process one user message through Gemini, tool calls, and state update."""

        self._extract_session_facts(user_text)
        if self._is_emergency(user_text):
            response = "⚠️ DISCONNECT POWER NOW\n\nUnplug USB/power immediately, step back, and let components cool before touching the board."
            self.session.add_history("assistant", response)
            return response

        # Convert state-aware natural-language proceed phrases to empty string so the
        # agent's deterministic handlers (INSTRUCT, VERIFY) fire instead of chat.
        if user_text.strip() and self._is_proceed_command(user_text):
            user_text = ""

        if user_text.strip():
            self.session.add_history("user", user_text.strip())
        else:
            self.session.add_history("user", "(continue)")

        if self._is_manual_confirm(user_text):
            return self.manual_confirm_current_step()
        if self.session.current_state == SessionState.PLAN and self.session.placement_plan and not user_text.strip():
            self.session.apply_transition(SessionState.INSTRUCT)
            return self._handle_instruction_state()
        if self.session.current_state == SessionState.INSTRUCT and self.session.placement_plan:
            return self._handle_instruction_state()
        if self.session.current_state == SessionState.VERIFY and self.session.placement_plan:
            if user_text.strip():
                return self._handle_verify_conversation()
            return self._handle_verify_state()
        if self.session.current_state == SessionState.VERIFY_COMPLETE:
            return self._handle_verify_complete_state()
        if self.session.current_state == SessionState.TEST:
            return self._handle_test_state()

        final_text = ""
        for _ in range(self.max_tool_rounds):
            declarations = self.tools.function_declarations(self.session.current_state.value)
            allowed_tool_names = {item["name"] for item in declarations}
            turn = self.model_client.generate(self.session, declarations)
            if turn.tool_calls:
                for tool_call in turn.tool_calls:
                    if tool_call.name not in allowed_tool_names:
                        result = {
                            "ok": False,
                            "error": f"Tool {tool_call.name!r} is not allowed in state {self.session.current_state.value}.",
                        }
                    else:
                        result = self.tools.execute(tool_call.name, tool_call.args)
                    self._record_tool_result(tool_call.name, result)
                if self.session.current_state == SessionState.INSTRUCT:
                    self._ensure_plan()
                    return self._handle_instruction_state()
                continue

            final_text = turn.text
            break
        else:
            final_text = self._fallback_state_response("Tool loop limit reached; pausing for user review.")

        clean_text = self._commit_response(final_text)
        return clean_text

    def _handle_instruction_state(self) -> str:
        """Prepare, annotate, and show the current planned step deterministically."""

        self._ensure_plan()
        step = self._current_plan_step()
        annotations = self._annotations_for_step(step)
        annotations.setdefault("step", step.get("step", self.current_step_number))

        if self.tools.annotation_uses_camera:
            capture = self.tools.execute("capture_frame", {})
            self._record_tool_result("capture_frame", capture)
            if not capture.get("ok"):
                text = (
                    "I could not capture the webcam frame. Check the webcam connection and lighting, "
                    "then say **retry** to try again."
                )
                return self._commit_response(self._state_response(text, SessionState.VERIFY, "camera capture failed"))
        else:
            prepared = self.tools.prepare_annotation_frame()
            self._record_tool_result("prepare_annotation_frame", prepared)
            if not prepared.get("ok"):
                text = (
                    "I could not prepare the reference breadboard image for annotation. "
                    "Check overlay.reference_image_path or switch overlay.annotation_source to camera.\n\n"
                    f"{prepared.get('error', 'Unknown annotation frame error')}"
                )
                return self._commit_response(self._state_response(text, SessionState.INSTRUCT, "annotation frame failed"))

        annotated = self.tools.execute("annotate_frame", {"annotations": annotations})
        self._record_tool_result("annotate_frame", annotated)
        if annotated.get("ok"):
            shown = self.tools.execute("show_annotated_frame", {})
            self._record_tool_result("show_annotated_frame", shown)
        else:
            text = (
                "I could not produce visible annotation data for this step. "
                "I am staying at the instruction checkpoint so the plan can be corrected.\n\n"
                f"{annotated.get('error', 'Unknown annotation error')}"
            )
            return self._commit_response(self._state_response(text, SessionState.INSTRUCT, "annotation missing"))

        instruction = str(step.get("instruction", "Place the next component as annotated."))
        text = (
            f"{instruction}\n\n"
            "When you've placed it, say **ready** to run the camera check — "
            "or **looks good** if you'd prefer to confirm yourself."
        )
        return self._commit_response(self._state_response(text, SessionState.VERIFY, "instruction shown"))

    def _annotations_for_step(self, step: dict[str, Any]) -> dict[str, Any]:
        """Return visible annotations, deriving simple hole markers when needed."""

        annotations = dict(step.get("annotations", {})) if isinstance(step.get("annotations"), dict) else {}
        annotations = self._complete_connection_annotations(annotations, step)
        if self._has_renderable_annotations(annotations):
            annotations.setdefault("message", step.get("instruction", ""))
            return self._attach_carryover_wires(annotations)

        source = " ".join(
            str(value)
            for value in (
                step.get("instruction", ""),
                step.get("verification", ""),
                annotations.get("message", ""),
            )
            if value
        )

        holes: list[tuple[str, int]] = []
        for row, col_text in HOLE_REF_RE.findall(source):
            hole = (row.upper(), int(col_text))
            if hole not in holes:
                holes.append(hole)

        if not holes:
            # Fallback for instructions like "connect to column 10" with no row letter.
            for col in self._extract_column_refs(source):
                hole = ("J", col)
                if hole not in holes:
                    holes.append(hole)

        if holes:
            annotations["points"] = [
                {"row": row, "col": col, "label": f"{row}{col}"}
                for row, col in holes
            ]
            if len(holes) >= 2:
                start_row, start_col = holes[0]
                end_row, end_col = holes[1]
                annotations["arrows"] = [
                    {
                        "from": {"row": start_row, "col": start_col},
                        "to": {"row": end_row, "col": end_col},
                        "label": str(step.get("step", "place")),
                    }
                ]
        else:
            rail_points = self._derive_rail_points(source)
            if rail_points:
                annotations["points"] = rail_points
                first = rail_points[0]
                second = rail_points[1] if len(rail_points) > 1 else None
                if second and str(first.get("rail", "")).lower() == str(second.get("rail", "")).lower():
                    annotations["arrows"] = [
                        {
                            "from": self._location_payload(first),
                            "to": self._location_payload(second),
                            "label": "rail",
                        }
                    ]

        annotations.setdefault("message", str(step.get("instruction", "")).strip())
        return self._attach_carryover_wires(annotations)

    def _complete_connection_annotations(
        self,
        annotations: dict[str, Any],
        step: dict[str, Any],
    ) -> dict[str, Any]:
        """Ensure wiring steps include both source and destination endpoints."""

        source = self._annotation_source_text(step, annotations)
        if not self._looks_like_wiring_text(source):
            return annotations

        arduino_points = self._derive_arduino_pin_points(source)
        if not arduino_points:
            return annotations

        points = [point for point in annotations.get("points", []) if isinstance(point, dict)]
        target_points = [point for point in points if self._is_renderable_location(point) and "arduino_pin" not in point]

        if not target_points:
            target_points = self._derive_breadboard_target_points(source)

        if not target_points:
            return annotations

        updated_points = list(points)
        for point in arduino_points + target_points:
            self._append_unique_location(updated_points, point)
        annotations["points"] = updated_points

        arrows = [arrow for arrow in annotations.get("arrows", []) if isinstance(arrow, dict)]
        pair_count = min(len(arduino_points), len(target_points))
        if pair_count == 0:
            return annotations

        for index in range(pair_count):
            arrow = {
                "from": self._location_payload(arduino_points[index]),
                "to": self._location_payload(target_points[index]),
                "label": str(target_points[index].get("label") or arduino_points[index].get("label") or "jumper"),
            }
            if not self._has_equivalent_arrow(arrows, arrow):
                arrows.append(arrow)
        annotations["arrows"] = arrows
        return annotations

    @staticmethod
    def _annotation_source_text(step: dict[str, Any], annotations: dict[str, Any]) -> str:
        return " ".join(
            str(value)
            for value in (
                step.get("title", ""),
                step.get("instruction", ""),
                step.get("verification", ""),
                annotations.get("message", ""),
            )
            if value
        )

    def _derive_breadboard_target_points(self, text: str) -> list[dict[str, Any]]:
        holes: list[dict[str, Any]] = []
        for match in HOLE_REF_RE.finditer(text):
            row, col_text = match.groups()
            if ARDUINO_ENDPOINT_RE.fullmatch(f"{row}{col_text}"):
                continue
            point = {"row": row.upper(), "col": int(col_text), "label": f"{row.upper()}{int(col_text)}"}
            self._append_unique_location(holes, point)

        if not holes:
            for col in self._extract_column_refs(text):
                self._append_unique_location(holes, {"row": "J", "col": col, "label": f"J{col}"})

        rail_points = self._derive_rail_points(text)
        for point in rail_points:
            self._append_unique_location(holes, point)
        return holes

    @staticmethod
    def _derive_arduino_pin_points(text: str) -> list[dict[str, Any]]:
        points: list[dict[str, Any]] = []
        for match in ARDUINO_ENDPOINT_RE.findall(text):
            pin = CircuitSenseiAgent._normalize_arduino_pin(match)
            point = {"arduino_pin": pin, "label": pin}
            CircuitSenseiAgent._append_unique_location(points, point)
        return points

    @staticmethod
    def _normalize_arduino_pin(pin: str) -> str:
        normalized = pin.upper().replace(" ", "")
        return ARDUINO_PIN_ALIASES.get(normalized, normalized)

    @staticmethod
    def _append_unique_location(points: list[dict[str, Any]], point: dict[str, Any]) -> None:
        location = CircuitSenseiAgent._location_payload(point)
        for existing in points:
            if CircuitSenseiAgent._location_payload(existing) == location:
                return
        points.append(point)

    @staticmethod
    def _has_equivalent_arrow(arrows: list[dict[str, Any]], candidate: dict[str, Any]) -> bool:
        candidate_start = candidate.get("from", {})
        candidate_end = candidate.get("to", {})
        for arrow in arrows:
            start = arrow.get("from")
            end = arrow.get("to")
            if start == candidate_start and end == candidate_end:
                return True
            if start == candidate_end and end == candidate_start:
                return True
        return False

    def _attach_carryover_wires(self, annotations: dict[str, Any]) -> dict[str, Any]:
        carryover_wires = self._previous_wire_segments()
        if carryover_wires:
            annotations["carryover_wires"] = carryover_wires
        return annotations

    def _previous_wire_segments(self) -> list[dict[str, Any]]:
        if not self.session.placement_plan or self.session.current_step <= 0:
            return []

        carryover: list[dict[str, Any]] = []
        seen: set[str] = set()
        prior_steps = self.session.placement_plan[: min(self.session.current_step, len(self.session.placement_plan))]
        for step in prior_steps:
            for wire in self._wire_segments_from_step(step):
                signature = self._wire_signature(wire)
                if signature in seen:
                    continue
                seen.add(signature)
                carryover.append({"from": wire["from"], "to": wire["to"]})
        return carryover

    def _wire_segments_from_step(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        annotations = step.get("annotations", {})
        if not isinstance(annotations, dict):
            return []

        context = " ".join(
            str(value)
            for value in (
                step.get("title", ""),
                step.get("instruction", ""),
                step.get("verification", ""),
                annotations.get("message", ""),
            )
            if value
        )

        wires: list[dict[str, Any]] = []
        for wire in annotations.get("wires", []):
            normalized = self._normalize_wire_segment(wire)
            if normalized:
                wires.append(normalized)

        for arrow in annotations.get("arrows", []):
            normalized = self._normalize_wire_segment(arrow)
            if not normalized:
                continue
            if self._is_wire_like_annotation(normalized, context):
                wires.append(normalized)

        if wires:
            return wires

        if not self._looks_like_wiring_text(context):
            return []

        points: list[dict[str, Any]] = []
        for point in annotations.get("points", []):
            if isinstance(point, dict) and self._is_renderable_location(point):
                points.append(self._location_payload(point))

        if len(points) < 2:
            return []

        # Pair sequential points to infer explicit wire segments when the step text is wiring-focused.
        derived: list[dict[str, Any]] = []
        for index in range(0, len(points) - 1, 2):
            derived.append({"from": points[index], "to": points[index + 1]})
        return derived

    @staticmethod
    def _normalize_wire_segment(candidate: Any) -> dict[str, Any] | None:
        if not isinstance(candidate, dict):
            return None
        start = candidate.get("from")
        end = candidate.get("to")
        if not isinstance(start, dict) or not isinstance(end, dict):
            return None
        if not CircuitSenseiAgent._is_renderable_location(start) or not CircuitSenseiAgent._is_renderable_location(end):
            return None

        normalized = {
            "from": CircuitSenseiAgent._location_payload(start),
            "to": CircuitSenseiAgent._location_payload(end),
        }
        label = str(candidate.get("label", "")).strip()
        if label:
            normalized["label"] = label
        return normalized

    @staticmethod
    def _is_wire_like_annotation(annotation: dict[str, Any], context: str) -> bool:
        label = str(annotation.get("label", "")).lower().strip()
        if CircuitSenseiAgent._looks_like_wiring_text(label):
            return True
        if not CircuitSenseiAgent._looks_like_wiring_text(context):
            return False
        if CircuitSenseiAgent._looks_like_component_text(label):
            return False
        return True

    @staticmethod
    def _looks_like_wiring_text(text: str) -> bool:
        lowered = text.lower()
        if any(token in lowered for token in WIRE_HINT_TOKENS):
            return True
        return bool(ARDUINO_PIN_RE.search(lowered))

    @staticmethod
    def _looks_like_component_text(text: str) -> bool:
        lowered = text.lower()
        if any(token in lowered for token in COMPONENT_HINT_TOKENS):
            return True
        return bool(re.search(r"\br\d+\b", lowered))

    @staticmethod
    def _wire_signature(annotation: dict[str, Any]) -> str:
        start = json.dumps(annotation.get("from", {}), sort_keys=True)
        end = json.dumps(annotation.get("to", {}), sort_keys=True)
        return "|".join(sorted((start, end)))

    @staticmethod
    def _has_renderable_annotations(annotations: dict[str, Any]) -> bool:
        points = annotations.get("points", [])
        for point in points if isinstance(points, list) else []:
            if isinstance(point, dict) and CircuitSenseiAgent._is_renderable_location(point):
                return True

        arrows = annotations.get("arrows", [])
        for arrow in arrows if isinstance(arrows, list) else []:
            if not isinstance(arrow, dict):
                continue
            start = arrow.get("from")
            end = arrow.get("to")
            if isinstance(start, dict) and isinstance(end, dict):
                if CircuitSenseiAgent._is_renderable_location(start) and CircuitSenseiAgent._is_renderable_location(end):
                    return True
        return False

    @staticmethod
    def _is_renderable_location(location: dict[str, Any]) -> bool:
        if "row" in location and "col" in location:
            return True
        if "arduino_pin" in location:
            return True
        if "rail" in location:
            return True
        if "x" in location and "y" in location:
            return True
        return False

    @staticmethod
    def _extract_column_refs(text: str) -> list[int]:
        columns: list[int] = []
        for value in COLUMN_REF_RE.findall(text):
            col = int(value)
            if col not in columns:
                columns.append(col)
        return columns

    @staticmethod
    def _location_payload(point: dict[str, Any]) -> dict[str, Any]:
        return {
            key: point[key]
            for key in ("row", "col", "arduino_pin", "rail", "side", "x", "y")
            if key in point
        }

    def _derive_rail_points(self, text: str) -> list[dict[str, Any]]:
        lowered = text.lower()
        if "rail" not in lowered:
            return []

        positive = any(token in lowered for token in ("positive rail", "(+)", "+ rail", "5v rail", "vcc rail"))
        negative = any(token in lowered for token in ("negative rail", "(-)", "- rail", "gnd rail", "ground rail"))
        if not positive and not negative:
            return []

        columns = self._extract_column_refs(text)
        points: list[dict[str, Any]] = []

        def add_rail(rail: str, col: int, label: str) -> None:
            point = {"rail": rail, "side": "right", "col": col, "label": label}
            if point not in points:
                points.append(point)

        if positive and negative:
            col = columns[0] if columns else 1
            add_rail("positive", col, "+ rail")
            add_rail("negative", col, "- rail")
            return points

        rail_name = "positive" if positive else "negative"
        label = "+ rail" if rail_name == "positive" else "- rail"
        if columns:
            add_rail(rail_name, columns[0], label)
            if len(columns) > 1:
                add_rail(rail_name, columns[1], label)
            return points

        # For "any hole in + rail" style steps, show a short rail segment.
        add_rail(rail_name, 1, label)
        add_rail(rail_name, min(5, max(2, self.tools.geometry.columns)), label)
        return points

    @staticmethod
    def _summarize_vision_analysis(raw: Any) -> str:
        """Convert Gemini Vision output into concise user-facing text."""

        if isinstance(raw, dict):
            payload = raw
            detail = payload.get("analysis")
            safety = payload.get("safety_concern")
            parts: list[str] = []
            if isinstance(detail, str) and detail.strip():
                parts.append(detail.strip())
            if isinstance(safety, str) and safety.strip() and safety.strip().lower() not in {"none", "null"}:
                parts.append(f"Safety concern: {safety.strip()}")
            if parts:
                return " ".join(parts)

        text = str(raw or "").strip()
        if not text:
            return "Placement did not match the requested step."

        clean = text
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\s*```$", "", clean)

        candidates = [clean]
        if "{" in clean and "}" in clean:
            candidates.append(clean[clean.find("{") : clean.rfind("}") + 1])

        for candidate in candidates:
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue

            if not isinstance(payload, dict):
                continue

            detail = payload.get("analysis")
            safety = payload.get("safety_concern")
            parts = []
            if isinstance(detail, str) and detail.strip():
                parts.append(detail.strip())
            if isinstance(safety, str) and safety.strip() and safety.strip().lower() not in {"none", "null"}:
                parts.append(f"Safety concern: {safety.strip()}")
            if parts:
                return " ".join(parts)

        return text

    def _handle_verify_state(self) -> str:
        """Capture the board and run Gemini Vision verification for the current step."""

        self._ensure_plan()
        step = self._current_plan_step()
        instruction = str(step.get("verification", step.get("instruction", "Verify the current placement.")))

        capture = self.tools.execute("capture_frame", {})
        self._record_tool_result("capture_frame", capture)
        if not capture.get("ok"):
            text = (
                "I could not capture the webcam frame. Check the camera connection, "
                "then say **retry** to try again."
            )
            return self._commit_response(self._state_response(text, SessionState.VERIFY, "camera capture failed"))

        analysis = self.tools.execute("analyze_board", {"instruction": instruction})
        self._record_tool_result("analyze_board", analysis)
        if not analysis.get("ok"):
            raw = analysis.get("analysis") or analysis.get("error") or ""
            summarized = self._summarize_vision_analysis(raw)
            detail = (
                "The camera service ran into a technical issue. This usually resolves on retry."
                if "failed" in str(raw).lower() or "exception" in str(raw).lower() or "error" in str(raw).lower()
                else summarized
            )
            text = (
                "The camera check couldn't complete. Say **retry** to try again, "
                f"or **looks good** to confirm the placement yourself.\n\n{detail}".rstrip()
            )
            return self._commit_response(self._state_response(text, SessionState.VERIFY, "vision check unavailable"))

        if bool(analysis.get("passed")):
            if self.session.current_step + 1 >= len(self.session.placement_plan):
                text = "Placement looks correct! All build steps are visually verified."
                return self._commit_response(self._state_response(text, SessionState.VERIFY_COMPLETE, "all steps verified"))
            text = "Placement looks correct! Say **ready** to continue to the next step."
            return self._commit_response(self._state_response(text, SessionState.INSTRUCT, "step verified"))

        details = self._summarize_vision_analysis(
            analysis.get("analysis", "Placement did not match the requested step.")
        )
        text = (
            "The camera check flagged an issue with this placement. "
            "Adjust it, then say **retry** to check again — "
            f"or **looks good** to confirm manually.\n\n{details}"
        )
        return self._commit_response(self._state_response(text, SessionState.VERIFY, "step needs correction"))

    def _handle_verify_complete_state(self) -> str:
        """Move from completed visual verification into controlled Arduino testing."""

        text = (
            "All visual build steps are verified. I will now run the Arduino-side validation. "
            "Keep the USB connection in place and do not change the breadboard wiring while the test runs."
        )
        return self._commit_response(self._state_response(text, SessionState.TEST, "ready for Arduino test"))

    def _handle_test_state(self) -> str:
        """Run the Arduino test deterministically instead of letting Gemini re-plan."""

        connect = self.tools.execute("arduino_connect", {"port": self.session.arduino_port})
        self._record_tool_result("arduino_connect", connect)
        if not connect.get("ok"):
            text = (
                "I could not connect to the Arduino yet, so I am staying in the test checkpoint. "
                f"Expected serial port: {connect.get('expected_port', self.session.arduino_port)}.\n\n"
                "Check the USB cable, Arduino IDE serial monitor, and config.yaml serial_port, then say **retry** to try again."
            )
            self.session.add_history("assistant", text)
            return text

        test_type, expected_values = self._test_spec()
        result = self.tools.execute("run_test_script", {"test_type": test_type, "expected_values": expected_values})
        self._record_tool_result("run_test_script", result)
        if not result.get("ok") and result.get("status") != "ok":
            text = (
                "The Arduino test command did not complete cleanly. I am staying in the test checkpoint so you can retry.\n\n"
                f"{json.dumps(result, indent=2, sort_keys=True)}"
            )
            self.session.add_history("assistant", text)
            return text

        passed = bool(result.get("passed", result.get("status") == "ok"))
        measurements = result.get("measurements", result)
        verdict = "PASS" if passed else "CHECK NEEDED"
        text = (
            f"Arduino test result: {verdict}\n\n"
            f"Test type: {test_type}\n"
            f"Measurements: {json.dumps(measurements, sort_keys=True)}\n\n"
            "Circuit-Sensei is back at IDLE. Start a new goal when you are ready."
        )
        return self._commit_response(self._state_response(text, SessionState.IDLE, "test complete"))

    def _test_spec(self) -> tuple[str, dict[str, Any]]:
        """Choose a simple Arduino validation routine for the current goal."""

        if "divider" in self.session.circuit_goal.lower():
            return "voltage_divider", {"expected_voltage": 2.5, "tolerance": 0.25, "pin": "A0"}
        if "button" in self.session.circuit_goal.lower():
            return "button", {"pin": 2}
        return "led", {"drive_pin": 9, "sense_pin": "A0"}

    def manual_confirm_current_step(self) -> str:
        """Manually mark the current verification step as passed."""

        if self.session.current_state != SessionState.VERIFY or not self.session.placement_plan:
            text = "Manual confirmation is only available while Circuit-Sensei is waiting to verify a build step."
            self.session.add_history("assistant", text)
            return text

        step_number = self.current_step_number
        if step_number and step_number not in self.session.verified_steps:
            self.session.verified_steps.append(step_number)
        self.session.add_history(
            "tool",
            CircuitSenseiTools.encode_tool_result(
                "manual_confirm",
                {"ok": True, "step": step_number, "message": "User manually confirmed placement."},
            ),
            name="manual_confirm",
        )

        if self.session.current_step + 1 >= len(self.session.placement_plan):
            self.session.current_step = len(self.session.placement_plan)
            self.session.apply_transition(SessionState.VERIFY_COMPLETE)
            text = (
                f"Step {step_number} confirmed. "
                "All build steps are verified — say **ready** to move on to Arduino testing."
            )
        else:
            self.session.current_step += 1
            self.session.apply_transition(SessionState.INSTRUCT)
            text = f"Step {step_number} confirmed. Say **ready** to continue to the next step."

        self.session.add_history("assistant", text)
        return text

    def _handle_verify_conversation(self) -> str:
        """Let the user talk to Gemini during verification without retrying vision."""

        declarations = self.tools.function_declarations(self.session.current_state.value)
        turn = self.model_client.generate(self.session, declarations)
        if turn.tool_calls:
            text = (
                "I'm still at the verification checkpoint. Say **retry** to re-run the camera check, "
                "or **looks good** to confirm the placement yourself."
            )
            self.session.add_history("assistant", text)
            return text

        try:
            clean_text, _ = parse_state_transition(turn.text)
        except Exception:
            clean_text = turn.text.strip()
        clean_text = PLAN_BLOCK_RE.sub("", clean_text).strip() or (
            "I'm still at the verification checkpoint. Say **retry** to re-run the camera check, "
            "or **looks good** to confirm manually."
        )
        self.session.add_history("assistant", clean_text)
        return clean_text

    def _commit_response(self, final_text: str) -> str:
        """Process a model/local response, update state, and store assistant history."""

        clean_text = self._process_model_text(final_text)
        self.session.add_history("assistant", clean_text)
        return clean_text

    def _record_tool_result(self, name: str, result: dict[str, Any]) -> None:
        if name == "arduino_connect" and result.get("ok"):
            self.session.arduino_connected = True
            self.session.arduino_port = str(result.get("port", self.session.arduino_port or ""))
        self.session.add_history("tool", CircuitSenseiTools.encode_tool_result(name, result), name=name)

    def _process_model_text(self, text: str) -> str:
        plan = parse_plan_block(text)
        accepted_plan = plan is not None and self.session.current_state in {
            SessionState.IDLE,
            SessionState.INTAKE,
            SessionState.PLAN,
        }
        if accepted_plan:
            self._set_plan(plan)

        components = parse_components_block(text)
        if components is not None:
            self.session.components = components

        try:
            clean_text, transition = parse_state_transition(text)
        except ValueError:
            clean_text = PLAN_BLOCK_RE.sub("", text).strip()
            transition = StateTransition(next_state=self._default_next_state(), reason="missing state block")

        previous_state = self.session.current_state
        requested_transition = transition
        transition = self._repair_transition(transition)
        jumped_to_instruction_before_plan = (
            previous_state in {SessionState.IDLE, SessionState.INTAKE}
            and requested_transition.next_state
            in {SessionState.INSTRUCT, SessionState.VERIFY, SessionState.VERIFY_COMPLETE, SessionState.TEST}
        )
        omitted_structured_plan = (
            not self.session.placement_plan
            and previous_state == SessionState.PLAN
            and requested_transition.next_state
            in {SessionState.INSTRUCT, SessionState.VERIFY, SessionState.VERIFY_COMPLETE, SessionState.TEST}
        )
        if (
            jumped_to_instruction_before_plan
            or omitted_structured_plan
            or self._should_synthesize_plan(previous_state, transition.next_state)
        ):
            if not self.session.placement_plan:
                self._ensure_plan()
            elif not self.session.components:
                self.session.components = build_builtin_components(self.session.circuit_goal)
            if previous_state == SessionState.PLAN and transition.next_state == SessionState.PLAN:
                transition = StateTransition(next_state=SessionState.INSTRUCT, reason="built-in plan ready")
            clean_text = summarize_plan_ready(self.session.circuit_goal)
        elif accepted_plan and previous_state in {SessionState.IDLE, SessionState.INTAKE, SessionState.PLAN}:
            if not self.session.components:
                self.session.components = build_builtin_components(self.session.circuit_goal)
            clean_text = summarize_plan_ready(self.session.circuit_goal)
        if previous_state == SessionState.PLAN and self.session.plan_repairs and "Adjusted for breadboard hole occupancy" not in clean_text:
            repair_text = "\n".join(f"- {repair}" for repair in self.session.plan_repairs)
            clean_text = f"{clean_text}\n\nAdjusted for breadboard hole occupancy:\n{repair_text}".strip()

        self.session.apply_transition(transition.next_state)
        self._advance_step_if_verified(previous_state, transition.next_state)
        clean_text = PLAN_BLOCK_RE.sub("", clean_text).strip()
        clean_text = COMPONENTS_BLOCK_RE.sub("", clean_text).strip()
        return clean_text

    def _set_plan(self, plan: list[dict[str, Any]]) -> None:
        """Replace the placement plan and reset step verification."""

        repaired, repairs = validate_and_repair_plan(plan)
        self.session.placement_plan = repaired
        self.session.plan_repairs = repairs
        self.session.current_step = 0
        self.session.verified_steps.clear()

    def _ensure_plan(self) -> None:
        """Create a built-in plan if the model did not provide one."""

        if not self.session.placement_plan:
            self._set_plan(build_builtin_plan(self.session.circuit_goal))
        if not self.session.components:
            self.session.components = build_builtin_components(self.session.circuit_goal)

    def _should_synthesize_plan(self, previous_state: SessionState, next_state: SessionState) -> bool:
        if self.session.placement_plan:
            return False
        if next_state == SessionState.INSTRUCT:
            return True
        return previous_state == SessionState.PLAN and next_state in {SessionState.PLAN, SessionState.INSTRUCT}

    def _repair_transition(self, transition: StateTransition) -> StateTransition:
        """Repair common live-model transition mistakes before strict validation."""

        current = self.session.current_state
        requested = transition.next_state
        if requested in ALLOWED_TRANSITIONS[current]:
            return transition

        if current == SessionState.IDLE and requested in {
            SessionState.PLAN,
            SessionState.INSTRUCT,
            SessionState.VERIFY,
            SessionState.VERIFY_COMPLETE,
            SessionState.TEST,
        } and self.session.circuit_goal and self.session.inventory:
            return StateTransition(SessionState.PLAN, "repaired skipped intake state")
        if current == SessionState.INTAKE and requested == SessionState.INSTRUCT:
            return StateTransition(SessionState.PLAN, "repaired skipped PLAN state")
        if current == SessionState.INTAKE and self.session.circuit_goal and self.session.inventory:
            return StateTransition(SessionState.PLAN, "repaired intake completion")
        if current == SessionState.PLAN and requested in {SessionState.VERIFY, SessionState.VERIFY_COMPLETE, SessionState.TEST}:
            return StateTransition(SessionState.INSTRUCT, "repaired skipped instruction state")
        if current == SessionState.INSTRUCT and requested == SessionState.INSTRUCT:
            return StateTransition(SessionState.VERIFY, "repaired repeated instruction state")

        return StateTransition(self._default_next_state(), f"repaired invalid transition to {requested.value}")

    def _default_next_state(self) -> SessionState:
        """Return a deterministic safe transition for the current state."""

        if self.session.current_state == SessionState.INTAKE and self.session.circuit_goal and self.session.inventory:
            return SessionState.PLAN
        if self.session.current_state == SessionState.IDLE and self.session.circuit_goal and self.session.inventory:
            return SessionState.PLAN
        if self.session.current_state == SessionState.PLAN and self.session.placement_plan:
            return SessionState.INSTRUCT
        return DETERMINISTIC_FALLBACKS[self.session.current_state]

    def _state_response(self, body: str, next_state: SessionState, reason: str) -> str:
        """Build a local response with the same state block Gemini uses."""

        return f"{body}\n\n%%STATE%%\n{json.dumps({'next_state': next_state.value, 'reason': reason})}\n%%END%%"

    def _current_plan_step(self) -> dict[str, Any]:
        """Return the current plan step, synthesizing a plan if needed."""

        self._ensure_plan()
        return self.session.placement_plan[min(self.session.current_step, len(self.session.placement_plan) - 1)]

    def _advance_step_if_verified(self, previous_state: SessionState, next_state: SessionState) -> None:
        if previous_state != SessionState.VERIFY:
            return
        if next_state not in {SessionState.INSTRUCT, SessionState.VERIFY_COMPLETE}:
            return
        if not self._last_analysis_passed():
            return

        step_number = self.current_step_number
        if step_number and step_number not in self.session.verified_steps:
            self.session.verified_steps.append(step_number)

        if next_state == SessionState.INSTRUCT:
            self.session.current_step = min(self.session.current_step + 1, max(len(self.session.placement_plan) - 1, 0))
        elif next_state == SessionState.VERIFY_COMPLETE:
            self.session.current_step = len(self.session.placement_plan)

    @property
    def current_step_number(self) -> int:
        """Return the 1-based current step number, or 0 if there is no plan."""

        if not self.session.placement_plan:
            return 0
        return min(self.session.current_step + 1, len(self.session.placement_plan))

    def _last_analysis_passed(self) -> bool:
        for entry in reversed(self.session.conversation_history):
            if entry.get("role") == "tool" and entry.get("name") == "analyze_board":
                content = str(entry.get("content", ""))
                return '"passed": true' in content.lower()
        return False

    def _extract_session_facts(self, user_text: str) -> None:
        text = user_text.strip()
        if not text:
            return

        goal_match = re.search(r"(?:goal|build|make)\s*:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        inv_match = re.search(r"(?:inventory|components|available)\s*:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        have_match = re.search(r"\bi\s+have\s+(.+?)(?:\.|\n|$)", text, re.IGNORECASE)
        if goal_match:
            self.session.circuit_goal = goal_match.group(1).strip()
        elif have_match and self.session.current_state in {SessionState.IDLE, SessionState.INTAKE} and not self.session.circuit_goal:
            self.session.circuit_goal = text[: have_match.start()].strip(" .") or text
        elif self.session.current_state in {SessionState.IDLE, SessionState.INTAKE} and not self.session.circuit_goal:
            self.session.circuit_goal = text

        if inv_match:
            raw_inventory = inv_match.group(1)
            self.session.inventory = [item.strip() for item in re.split(r"[,;]", raw_inventory) if item.strip()]
        elif have_match:
            raw_inventory = have_match.group(1)
            self.session.inventory = [
                re.sub(r"^(?:and|a|an)\s+", "", item.strip(), flags=re.IGNORECASE)
                for item in re.split(r",|;", raw_inventory.replace(" and ", ", "))
                if item.strip()
            ]

    def _is_emergency(self, user_text: str) -> bool:
        return bool(re.search(r"\b(smoke|hot|heat|burn|burning|melting)\b", user_text, re.IGNORECASE))

    def _is_proceed_command(self, user_text: str) -> bool:
        """Return True when the user clearly means 'continue/retry' in the current state."""
        if self.session.current_state not in {
            SessionState.PLAN, SessionState.INSTRUCT, SessionState.VERIFY, SessionState.VERIFY_COMPLETE,
        }:
            return False
        text = user_text.strip().lower().rstrip(".,!?;:")
        return text in {
            "next", "continue", "proceed", "go", "go ahead", "move on",
            "ready", "i'm ready", "im ready", "ok", "okay",
            "retry", "try again", "check again", "re-check", "recheck", "check",
            "done", "placed", "placed it", "i placed it", "i'm done", "im done",
            "all done", "it's in", "its in", "let's go", "lets go",
            "yep", "yes", "sure", "go on",
        }

    def _is_manual_confirm(self, user_text: str) -> bool:
        text = user_text.strip().lower().rstrip(".,!?;:")
        if text in {
            "/confirm",
            "confirm",
            "confirmed",
            "manual confirm",
            "manually confirm",
            "looks good",
            "it looks good",
            "looks correct",
            "it looks correct",
            "all good",
            "it's good",
            "its good",
            "i checked",
            "i checked it",
            "i verified",
            "i verified it",
            "it's correct",
            "its correct",
            "it's right",
            "its right",
            "skip vision",
            "trust me",
            "verified",
            "accept",
        }:
            return True
        return bool(re.fullmatch(r"(i\s+)?(confirm|verified?|checked)(\s+it)?", text))

    def _fallback_state_response(self, body: str) -> str:
        next_state = self._default_next_state()
        return self._state_response(body, next_state, "fallback")


def parse_state_transition(text: str) -> tuple[str, StateTransition]:
    """Parse and remove the required Gemini state transition block."""

    match = STATE_BLOCK_RE.search(text)
    if not match:
        raise ValueError("Model response did not include a %%STATE%% transition block.")
    payload = json.loads(match.group(1))
    next_state = SessionState(str(payload["next_state"]))
    reason = str(payload.get("reason", ""))
    clean = STATE_BLOCK_RE.sub("", text).strip()
    return clean, StateTransition(next_state=next_state, reason=reason)


def parse_plan_block(text: str) -> list[dict[str, Any]] | None:
    """Parse an optional placement plan JSON block."""

    match = PLAN_BLOCK_RE.search(text)
    if not match:
        return None
    payload = json.loads(match.group(1))
    if not isinstance(payload, list):
        raise ValueError("Plan JSON block must be a list.")
    return [dict(item) for item in payload]


def parse_components_block(text: str) -> list[str] | None:
    """Parse an optional components list JSON block."""

    match = COMPONENTS_BLOCK_RE.search(text)
    if not match:
        return None
    payload = json.loads(match.group(1))
    if not isinstance(payload, list):
        return None
    return [str(item) for item in payload]


def create_model_client(config: dict[str, Any]) -> ModelClient:
    """Create a mock or real Gemini model client from configuration."""

    gemini = config.get("gemini", {})
    hardware = config.get("hardware", {})
    if config_bool(hardware.get("mock_mode"), default=True):
        return MockGeminiModelClient()
    return GeminiModelClient(
        model=str(gemini.get("model", "gemini-2.5-flash")),
        retries=int(gemini.get("retries", 3)),
    )
