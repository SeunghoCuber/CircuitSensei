from __future__ import annotations

import sys
import types

from circuit_sensei.hardware.arduino_tester import ArduinoTester


def test_real_connect_clears_startup_banner(monkeypatch) -> None:
    fake_serial = _FakeSerial([b'{"status":"ok","message":"Circuit-Sensei tester ready"}\n', b'{"status":"ok","value":2.502,"unit":"V"}\n'])
    serial_module = types.SimpleNamespace(Serial=lambda *args, **kwargs: fake_serial)
    monkeypatch.setitem(sys.modules, "serial", serial_module)
    monkeypatch.setattr("circuit_sensei.hardware.arduino_tester.time.sleep", lambda seconds: None)

    tester = ArduinoTester(port="/dev/fake", mock_mode=False)

    assert tester.connect()["ok"] is True
    assert fake_serial.reset_called is True
    assert tester.send_command("READ_ANALOG", {"pin": "A0"}) == {"status": "ok", "value": 2.502, "unit": "V"}
    assert fake_serial.writes == [b'{"cmd":"read_analog","pin":0}\n']


def test_real_voltage_divider_script_uses_read_analog(monkeypatch) -> None:
    fake_serial = _FakeSerial([b'{"status":"ok","pin":0,"raw":512,"voltage":2.5}\n'])
    tester = ArduinoTester(port="/dev/fake", mock_mode=False, _serial=fake_serial)

    result = tester.run_test_script("voltage_divider", {"pin": "A0", "expected_voltage": 2.5, "tolerance": 0.1})

    assert result == {
        "status": "ok",
        "test_type": "voltage_divider",
        "measurements": {"midpoint_voltage": 2.5},
        "passed": True,
    }
    assert fake_serial.writes == [b'{"cmd":"read_analog","pin":0}\n']


def test_real_command_retries_transient_parse_error(monkeypatch) -> None:
    fake_serial = _FakeSerial(
        [
            b'{"status":"error","msg":"parse error"}\n',
            b'{"status":"ok","pin":0,"raw":512,"voltage":2.5}\n',
        ]
    )
    monkeypatch.setattr("circuit_sensei.hardware.arduino_tester.time.sleep", lambda seconds: None)
    tester = ArduinoTester(port="/dev/fake", mock_mode=False, _serial=fake_serial)

    result = tester.send_command("READ_ANALOG", {"pin": "A0"})

    assert result == {"status": "ok", "pin": 0, "raw": 512, "voltage": 2.5, "value": 2.5, "unit": "V"}
    assert fake_serial.writes == [b'{"cmd":"read_analog","pin":0}\n', b'{"cmd":"read_analog","pin":0}\n']
    assert fake_serial.reset_called is True


def test_close_releases_serial_connection() -> None:
    fake_serial = _FakeSerial([])
    tester = ArduinoTester(port="/dev/fake", mock_mode=False, _serial=fake_serial)

    tester.close()

    assert fake_serial.closed is True
    assert tester._serial is None


class _FakeSerial:
    def __init__(self, lines: list[bytes]) -> None:
        self.lines = lines
        self.writes: list[bytes] = []
        self.reset_called = False
        self.closed = False

    def write(self, line: bytes) -> None:
        self.writes.append(line)

    def readline(self) -> bytes:
        if self.lines:
            return self.lines.pop(0)
        return b""

    def reset_input_buffer(self) -> None:
        self.reset_called = True
        if self.lines and b"Circuit-Sensei tester ready" in self.lines[0]:
            self.lines.pop(0)

    def close(self) -> None:
        self.closed = True
