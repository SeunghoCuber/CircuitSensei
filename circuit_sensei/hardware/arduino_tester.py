"""USB serial Arduino tester for Circuit-Sensei."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any


class ArduinoUnavailableError(RuntimeError):
    """Raised when Arduino serial hardware is required but unavailable."""


AUTO_PORT_VALUES = {"", "auto", "detect", "default"}
KNOWN_ARDUINO_VIDS = {0x2341, 0x2A03}
USB_SERIAL_VIDS = {0x1A86, 0x10C4, 0x0403, 0x239A}
EXCLUDED_PORT_KEYWORDS = ("bluetooth", "incoming-port")
ARDUINO_KEYWORDS = ("arduino", "genuino", "uno", "usbmodem", "ttyacm")
USB_SERIAL_KEYWORDS = ("ch340", "ch341", "cp210", "ftdi", "usb serial", "usb2.0-serial", "usbserial")


@dataclass(frozen=True)
class SerialPortCandidate:
    """A ranked serial device that may be an Arduino."""

    device: str
    label: str
    score: int


def normalize_serial_port(port: Any, default: str = "auto") -> str:
    """Return a usable serial-port config value."""

    text = str(port or "").strip()
    return text or default


@dataclass
class ArduinoTester:
    """Send structured commands to the Circuit-Sensei Arduino sketch."""

    port: str
    baud_rate: int = 115200
    timeout_seconds: float = 2.0
    mock_mode: bool = True
    command_attempts: int = 2
    _serial: Any = None

    @property
    def connected(self) -> bool:
        """Return whether the tester has an active connection."""

        return self.mock_mode or self._serial is not None

    def connect(self, port: str | None = None) -> dict[str, Any]:
        """Connect to the Arduino over USB serial, or create a mock connection."""

        if port is not None:
            self.port = port
        if self.mock_mode:
            return {"ok": True, "port": self.port, "mock": True, "message": "Mock Arduino connected."}

        try:
            import serial  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ArduinoUnavailableError("pyserial is not installed. Install requirements.txt.") from exc

        self.close()

        attempted: list[str] = []
        failures: list[str] = []
        ports = self._candidate_ports(serial)
        if not ports:
            raise ArduinoUnavailableError("No Arduino serial port detected. Connect the Arduino over USB and retry.")

        for candidate in ports:
            attempted.append(candidate)
            try:
                self._serial = serial.Serial(candidate, self.baud_rate, timeout=self.timeout_seconds)
                self.port = candidate
                time.sleep(2.0)
                self._clear_serial_input()
                return {"ok": True, "port": self.port, "mock": False, "message": "Arduino connected."}
            except Exception as exc:  # pragma: no cover - depends on local hardware
                if self._serial is not None:
                    try:
                        self._serial.close()
                    except Exception:
                        pass
                self._serial = None
                failures.append(f"{candidate}: {exc}")

        detail = "; ".join(failures) or ", ".join(attempted)
        raise ArduinoUnavailableError(
            "Arduino unavailable on detected serial port"
            f"{'s' if len(attempted) != 1 else ''}: {', '.join(attempted)}. "
            "Check the USB cable, board, and Arduino IDE serial monitor."
            f" Details: {detail}"
        )

    def _candidate_ports(self, serial_module: Any) -> list[str]:
        """Return serial ports to attempt, preserving explicit overrides."""

        explicit_port = str(self.port or "").strip()
        if explicit_port.lower() not in AUTO_PORT_VALUES:
            return [explicit_port]

        candidates = self.discover_ports(serial_module)
        return [candidate.device for candidate in candidates]

    @classmethod
    def discover_ports(cls, serial_module: Any | None = None) -> list[SerialPortCandidate]:
        """Discover likely Arduino serial ports using pyserial list_ports metadata."""

        try:
            list_ports = cls._list_ports_module(serial_module)
            ports = list(list_ports.comports())
        except Exception as exc:
            raise ArduinoUnavailableError("Could not inspect serial ports with pyserial.") from exc

        candidates = [candidate for port_info in ports if (candidate := cls._rank_port(port_info))]
        candidates.sort(key=lambda candidate: (-candidate.score, candidate.device))
        return candidates

    @staticmethod
    def _list_ports_module(serial_module: Any | None = None) -> Any:
        """Return pyserial's list_ports module, supporting test doubles."""

        if serial_module is not None:
            tools = getattr(serial_module, "tools", None)
            list_ports = getattr(tools, "list_ports", None)
            if list_ports is not None:
                return list_ports

        from serial.tools import list_ports  # type: ignore[import-not-found]

        return list_ports

    @classmethod
    def _rank_port(cls, port_info: Any) -> SerialPortCandidate | None:
        """Score a serial port by how Arduino-like it appears."""

        device = str(getattr(port_info, "device", "") or "")
        if not device:
            return None

        fields = [
            device,
            str(getattr(port_info, "name", "") or ""),
            str(getattr(port_info, "description", "") or ""),
            str(getattr(port_info, "manufacturer", "") or ""),
            str(getattr(port_info, "product", "") or ""),
            str(getattr(port_info, "hwid", "") or ""),
        ]
        label = " ".join(field for field in fields if field)
        haystack = label.lower()
        if any(keyword in haystack for keyword in EXCLUDED_PORT_KEYWORDS):
            return None

        score = 0
        vid = getattr(port_info, "vid", None)
        if isinstance(vid, int):
            if vid in KNOWN_ARDUINO_VIDS:
                score += 100
            elif vid in USB_SERIAL_VIDS:
                score += 70

        if any(keyword in haystack for keyword in ARDUINO_KEYWORDS):
            score += 80
        if any(keyword in haystack for keyword in USB_SERIAL_KEYWORDS):
            score += 55
        if device.startswith("/dev/cu.usbmodem") or device.startswith("/dev/ttyACM"):
            score += 40
        if device.startswith("/dev/cu.usbserial") or device.startswith("/dev/ttyUSB"):
            score += 30

        if score <= 0:
            return None
        if device.startswith("/dev/cu."):
            score += 10

        return SerialPortCandidate(device=device, label=label, score=score)

    def send_command(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a JSON command and return the parsed Arduino response."""

        params = params or {}
        payload = self._hardware_payload(command, params)
        if self.mock_mode:
            return self._mock_response(payload)

        if self._serial is None:
            raise ArduinoUnavailableError(f"Arduino is not connected. Serial port target: {self.port}")

        attempts = max(1, self.command_attempts)
        response: dict[str, Any] | None = None
        for attempt in range(attempts):
            response = self._send_payload(command, payload)
            if not self._is_transient_parse_error(response) or attempt + 1 >= attempts:
                return response
            time.sleep(0.05)
            self._clear_serial_input()

        return response or {"status": "error", "msg": "no response"}

    def run_test_script(self, test_type: str, expected_values: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a named circuit validation routine using Arduino measurements."""

        expected_values = expected_values or {}
        if self.mock_mode:
            return self._mock_test(test_type, expected_values)

        test_type = test_type.lower().strip()
        if test_type == "voltage_divider":
            response = self.send_command("READ_ANALOG", {"pin": expected_values.get("pin", "A0")})
            volts = float(response.get("value", response.get("voltage", 0.0)))
            expected = float(expected_values.get("expected_voltage", volts))
            tolerance = float(expected_values.get("tolerance", 0.25))
            return {
                "status": response.get("status", "ok"),
                "test_type": test_type,
                "measurements": {"midpoint_voltage": round(volts, 3)},
                "passed": abs(volts - expected) <= tolerance,
            }
        if test_type == "button":
            response = self.send_command("READ_DIGITAL", {"pin": expected_values.get("pin", 2)})
            return {
                "status": response.get("status", "ok"),
                "test_type": test_type,
                "measurements": {"digital": response.get("value")},
                "passed": response.get("status") == "ok",
            }
        if test_type == "led":
            drive_pin = int(expected_values.get("drive_pin", 9))
            sense_pin = expected_values.get("sense_pin", "A0")
            try:
                self.send_command("SET_DIGITAL", {"pin": drive_pin, "value": 1})
                time.sleep(2.0)
                response = self.send_command("READ_ANALOG", {"pin": sense_pin})
            finally:
                self.send_command("SET_DIGITAL", {"pin": drive_pin, "value": 0})
            volts = float(response.get("value", response.get("voltage", 0.0)))
            return {
                "status": response.get("status", "ok"),
                "test_type": test_type,
                "measurements": {"drive_pin": f"D{drive_pin}", "sense_voltage": round(volts, 3)},
                "passed": response.get("status") == "ok",
            }

        return self.send_command("RUN_TEST", {"test_type": test_type, **expected_values})

    def close(self) -> None:
        """Close the active serial connection, if any."""

        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def _clear_serial_input(self) -> None:
        """Discard startup banners or stale bytes before command/response traffic."""

        if self._serial is not None and hasattr(self._serial, "reset_input_buffer"):
            self._serial.reset_input_buffer()

    def _send_payload(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send one JSON payload and return the parsed response."""

        if self._serial is None:
            raise ArduinoUnavailableError(f"Arduino is not connected. Serial port target: {self.port}")

        line = json.dumps(payload, separators=(",", ":")) + "\n"
        self._serial.write(line.encode("utf-8"))
        raw = self._serial.readline().decode("utf-8", errors="replace").strip()
        if not raw:
            raise TimeoutError(f"No Arduino response for command {command!r}.")
        try:
            return self._normalize_response(command, json.loads(raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Arduino returned non-JSON response: {raw}") from exc

    def _hardware_payload(self, command: str, params: dict[str, Any]) -> dict[str, Any]:
        """Return the JSON payload expected by the Arduino firmware."""

        wire_command = command.lower().strip()
        payload = {"cmd": wire_command, **params}
        if wire_command == "read_analog" and "pin" in payload:
            payload["pin"] = self._analog_channel(payload["pin"])
        return payload

    def _normalize_response(self, command: str, response: dict[str, Any]) -> dict[str, Any]:
        """Expose stable response keys across compatible Arduino sketches."""

        if command.upper().strip() == "READ_ANALOG" and "voltage" in response and "value" not in response:
            response = {**response, "value": response["voltage"], "unit": "V"}
        return response

    def _is_transient_parse_error(self, response: dict[str, Any]) -> bool:
        """Return whether a response is safe to retry after serial reset noise."""

        message = str(response.get("msg", response.get("message", ""))).lower()
        return response.get("status") == "error" and "parse" in message

    def _analog_channel(self, pin: Any) -> Any:
        """Convert A0-style analog pin names to channel numbers for firmware dialects."""

        if isinstance(pin, str) and pin.upper().startswith("A"):
            suffix = pin[1:]
            if suffix.isdigit():
                return int(suffix)
        return pin

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
