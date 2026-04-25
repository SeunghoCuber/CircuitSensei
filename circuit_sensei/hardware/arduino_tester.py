"""USB serial Arduino tester for Circuit-Sensei."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any


class ArduinoUnavailableError(RuntimeError):
    """Raised when Arduino serial hardware is required but unavailable."""


@dataclass
class ArduinoTester:
    """Send structured commands to the Circuit-Sensei Arduino sketch."""

    port: str
    baud_rate: int = 115200
    timeout_seconds: float = 2.0
    mock_mode: bool = True
    _serial: Any = None

    @property
    def connected(self) -> bool:
        """Return whether the tester has an active connection."""

        return self.mock_mode or self._serial is not None

    def connect(self, port: str | None = None) -> dict[str, Any]:
        """Connect to the Arduino over USB serial, or create a mock connection."""

        if port:
            self.port = port
        if self.mock_mode:
            return {"ok": True, "port": self.port, "mock": True, "message": "Mock Arduino connected."}

        try:
            import serial  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ArduinoUnavailableError("pyserial is not installed. Install requirements.txt.") from exc

        try:
            self._serial = serial.Serial(self.port, self.baud_rate, timeout=self.timeout_seconds)
            time.sleep(2.0)
        except Exception as exc:  # pragma: no cover - depends on local hardware
            raise ArduinoUnavailableError(
                f"Arduino unavailable on {self.port}. Check the USB cable, board, and expected serial port."
            ) from exc

        return {"ok": True, "port": self.port, "mock": False, "message": "Arduino connected."}

    def send_command(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a JSON command and return the parsed Arduino response."""

        params = params or {}
        payload = {"cmd": command, **params}
        if self.mock_mode:
            return self._mock_response(payload)

        if self._serial is None:
            raise ArduinoUnavailableError(f"Arduino is not connected. Expected serial port: {self.port}")

        line = json.dumps(payload, separators=(",", ":")) + "\n"
        self._serial.write(line.encode("utf-8"))
        raw = self._serial.readline().decode("utf-8", errors="replace").strip()
        if not raw:
            raise TimeoutError(f"No Arduino response for command {command!r}.")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Arduino returned non-JSON response: {raw}") from exc

    def run_test_script(self, test_type: str, expected_values: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a named circuit validation routine using Arduino measurements."""

        expected_values = expected_values or {}
        if self.mock_mode:
            return self._mock_test(test_type, expected_values)
        return self.send_command("RUN_TEST", {"test_type": test_type, "params": expected_values})

    def _mock_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        cmd = str(payload.get("cmd", "")).upper()
        if cmd == "READ_ANALOG":
            return {"status": "ok", "pin": payload.get("pin", "A0"), "value": 2.48, "unit": "V", "mock": True}
        if cmd == "READ_DIGITAL":
            return {"status": "ok", "pin": payload.get("pin", 2), "value": 1, "mock": True}
        if cmd in {"SET_DIGITAL", "SET_PWM"}:
            return {"status": "ok", "cmd": cmd, "mock": True}
        if cmd == "RUN_TEST":
            return self._mock_test(str(payload.get("test_type", "generic")), dict(payload.get("params", {})))
        return {"status": "error", "error": f"Unsupported mock command {cmd!r}", "mock": True}

    def _mock_test(self, test_type: str, expected_values: dict[str, Any]) -> dict[str, Any]:
        test_type = test_type.lower().strip()
        if test_type == "voltage_divider":
            expected = float(expected_values.get("expected_voltage", 2.5))
            measured = expected + 0.03
            passed = abs(measured - expected) <= float(expected_values.get("tolerance", 0.15))
            return {
                "status": "ok",
                "test_type": test_type,
                "measurements": {"midpoint_voltage": round(measured, 3)},
                "passed": passed,
                "mock": True,
            }
        if test_type == "led":
            return {
                "status": "ok",
                "test_type": test_type,
                "measurements": {"drive_pin": "D9", "sense_voltage": 1.92},
                "passed": True,
                "mock": True,
            }
        if test_type == "button":
            return {
                "status": "ok",
                "test_type": test_type,
                "measurements": {"released": 1, "pressed": 0},
                "passed": True,
                "mock": True,
            }
        return {
            "status": "ok",
            "test_type": test_type or "generic",
            "measurements": {"analog_A0": 2.48},
            "passed": True,
            "mock": True,
        }
