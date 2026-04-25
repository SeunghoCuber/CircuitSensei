"""Smoke-test the Circuit-Sensei Arduino serial protocol.

This script exercises the same ArduinoTester class used by the agent while
keeping outputs inactive. It is intended for quick hardware bring-up before
running the full camera/Gemini workflow.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from circuit_sensei.hardware.arduino_tester import ArduinoTester  # noqa: E402


def load_hardware_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = dict(yaml.safe_load(handle) or {})
    return dict(config.get("hardware", {}))


def print_result(label: str, result: dict[str, Any]) -> None:
    print(f"{label}: {json.dumps(result, sort_keys=True)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test Arduino JSON-over-serial.")
    parser.add_argument("--config", default="config.yaml", help="Path to Circuit-Sensei config.")
    parser.add_argument("--port", default="", help="Override serial port, for example /dev/cu.usbmodem21301.")
    parser.add_argument("--baud", type=int, default=0, help="Override baud rate.")
    parser.add_argument("--timeout", type=float, default=0.0, help="Override serial timeout in seconds.")
    args = parser.parse_args()

    hardware = load_hardware_config(Path(args.config))
    port = args.port or str(hardware.get("serial_port", ""))
    baud = args.baud or int(hardware.get("baud_rate", 115200))
    timeout = args.timeout or float(hardware.get("serial_timeout_seconds", 2.0))

    if not port:
        print("No serial port configured. Pass --port or set hardware.serial_port in config.yaml.", file=sys.stderr)
        return 2

    tester = ArduinoTester(port=port, baud_rate=baud, timeout_seconds=timeout, mock_mode=False)
    try:
        print_result("connect", tester.connect())
        print_result("read_analog_A0", tester.send_command("READ_ANALOG", {"pin": "A0"}))
        print_result("read_digital_2", tester.send_command("READ_DIGITAL", {"pin": 2}))
        print_result("button_test", tester.run_test_script("button", {"pin": 2}))
    finally:
        tester.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
