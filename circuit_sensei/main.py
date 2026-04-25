"""Command-line entry point for Circuit-Sensei."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from circuit_sensei.agent import AgentSession, CircuitSenseiAgent, create_model_client
from circuit_sensei.hardware.overlay import BreadboardGeometry
from circuit_sensei.tools import CircuitSenseiTools


def load_config(path: str | Path) -> dict[str, Any]:
    """Load YAML configuration."""

    with Path(path).open("r", encoding="utf-8") as handle:
        return dict(yaml.safe_load(handle) or {})


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(description="Circuit-Sensei breadboard assistant")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config.")
    parser.add_argument("--mock", action="store_true", help="Force mock camera, vision, and Arduino mode.")
    parser.add_argument("--real", action="store_true", help="Use real Gemini, webcam, and Arduino hardware.")
    parser.add_argument("--goal", default="", help="Initial natural-language circuit goal.")
    parser.add_argument("--inventory", default="", help="Comma-separated component inventory.")
    parser.add_argument("--auto-demo", action="store_true", help="Advance automatically through the mock workflow.")
    parser.add_argument("--capture-test", action="store_true", help="Capture one camera frame and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Circuit-Sensei CLI."""

    args = build_parser().parse_args(argv)
    console = Console()
    config = load_config(args.config)
    config.setdefault("hardware", {})
    if args.mock:
        config["hardware"]["mock_mode"] = True
    if args.real:
        config["hardware"]["mock_mode"] = False

    mock_mode = bool(config["hardware"].get("mock_mode", True))
    if not mock_mode and not os.environ.get("GEMINI_API_KEY"):
        console.print("[red]GEMINI_API_KEY is missing. Set it or run with --mock.[/red]")
        return 2

    geometry = BreadboardGeometry.from_config(config)
    session = AgentSession(
        breadboard_geometry={
            "top_left": geometry.top_left,
            "bottom_right": geometry.bottom_right,
            "rows": geometry.rows,
            "columns": geometry.columns,
        },
        arduino_port=str(config.get("hardware", {}).get("serial_port", "")),
    )
    if args.goal:
        session.circuit_goal = args.goal
    if args.inventory:
        session.inventory = [item.strip() for item in args.inventory.split(",") if item.strip()]

    tools = CircuitSenseiTools(config, console=console)
    if args.capture_test:
        result = tools.capture_frame()
        if result.get("ok"):
            console.print_json(data=result)
            console.print(f"Open the frame with: open {result['path']}")
            return 0
        console.print_json(data=result)
        return 1

    model_client = create_model_client(config)
    agent = CircuitSenseiAgent(
        session=session,
        tools=tools,
        model_client=model_client,
        max_tool_rounds=int(config.get("gemini", {}).get("max_tool_rounds", 6)),
    )

    mode_label = "MOCK" if mock_mode else "REAL HARDWARE"
    console.print(
        Panel(
            "Circuit-Sensei is ready.\n"
            "Commands: /next to continue, /confirm to manually accept a step, /state to inspect state, /quit to exit.\n"
            "Guidance is drawn on-screen over webcam frames; no LED strips are used.",
            title=f"Circuit-Sensei ({mode_label})",
            border_style="cyan",
        )
    )

    if args.goal or args.inventory:
        seed = f"Goal: {session.circuit_goal}\nInventory: {', '.join(session.inventory)}"
        console.print(agent.handle_user_message(seed))
        if args.auto_demo:
            return run_auto_demo(agent, console)

    while True:
        text = Prompt.ask("[bold cyan]You[/bold cyan]", default="/next")
        command = text.strip().lower()
        if command in {"/quit", "quit", "exit"}:
            return 0
        if command == "/state":
            console.print_json(data=session.snapshot())
            continue
        if command in {"/confirm", "confirm", "confirmed", "manual confirm", "manually confirm"}:
            console.print(agent.manual_confirm_current_step())
            continue
        if command == "/next":
            text = ""

        try:
            response = agent.handle_user_message(text)
        except Exception as exc:
            console.print(f"[red]Circuit-Sensei error:[/red] {exc}")
            continue
        console.print(response)


def run_auto_demo(agent: CircuitSenseiAgent, console: Console) -> int:
    """Advance a mock session until it returns to IDLE or reaches a guard limit."""

    for _ in range(20):
        if agent.session.current_state.value == "IDLE" and agent.session.placement_plan:
            return 0
        response = agent.handle_user_message("")
        console.print(response)
    console.print("[yellow]Auto demo stopped after 20 turns.[/yellow]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
