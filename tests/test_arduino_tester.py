from __future__ import annotations

import sys
import types

import pytest

from circuit_sensei.hardware.arduino_tester import ArduinoTester, ArduinoUnavailableError, normalize_serial_port


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


def test_auto_connect_detects_likely_arduino_port(monkeypatch) -> None:
    fake_serial = _FakeSerial([])
    ports = [
        _PortInfo("/dev/cu.Bluetooth-Incoming-Port", description="Bluetooth-Incoming-Port"),
        _PortInfo("/dev/cu.usbserial-1410", description="USB2.0-Serial", manufacturer="wch.cn", vid=0x1A86),
        _PortInfo("/dev/cu.usbmodem11101", description="Arduino Uno", manufacturer="Arduino LLC", vid=0x2341),
    ]
    serial_module = _serial_module(fake_serial, ports)
    monkeypatch.setitem(sys.modules, "serial", serial_module)
    monkeypatch.setattr("circuit_sensei.hardware.arduino_tester.time.sleep", lambda seconds: None)

    tester = ArduinoTester(port="auto", mock_mode=False)

    result = tester.connect()

    assert result["ok"] is True
    assert result["port"] == "/dev/cu.usbmodem11101"
    assert tester.port == "/dev/cu.usbmodem11101"


def test_auto_connect_supports_usb_serial_arduino_clones(monkeypatch) -> None:
    fake_serial = _FakeSerial([])
    ports = [
        _PortInfo("/dev/cu.Bluetooth-Incoming-Port", description="Bluetooth-Incoming-Port"),
        _PortInfo("/dev/cu.usbserial-1410", description="USB2.0-Serial", manufacturer="wch.cn", vid=0x1A86),
    ]
    serial_module = _serial_module(fake_serial, ports)
    monkeypatch.setitem(sys.modules, "serial", serial_module)
    monkeypatch.setattr("circuit_sensei.hardware.arduino_tester.time.sleep", lambda seconds: None)

    tester = ArduinoTester(port="", mock_mode=False)

    assert tester.connect()["port"] == "/dev/cu.usbserial-1410"


def test_auto_connect_reports_when_no_candidate_port(monkeypatch) -> None:
    serial_module = _serial_module(_FakeSerial([]), [_PortInfo("/dev/cu.Bluetooth-Incoming-Port")])
    monkeypatch.setitem(sys.modules, "serial", serial_module)

    tester = ArduinoTester(port="auto", mock_mode=False)

    with pytest.raises(ArduinoUnavailableError, match="No Arduino serial port detected"):
        tester.connect()


def test_explicit_port_skips_autodetection(monkeypatch) -> None:
    fake_serial = _FakeSerial([])
    serial_module = _serial_module(fake_serial, [])
    monkeypatch.setitem(sys.modules, "serial", serial_module)
    monkeypatch.setattr("circuit_sensei.hardware.arduino_tester.time.sleep", lambda seconds: None)

    tester = ArduinoTester(port="/dev/manual", mock_mode=False)

    assert tester.connect()["port"] == "/dev/manual"


def test_normalize_serial_port_defaults_to_auto() -> None:
    assert normalize_serial_port("") == "auto"
    assert normalize_serial_port(None) == "auto"
    assert normalize_serial_port("/dev/cu.usbmodem11101") == "/dev/cu.usbmodem11101"


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


class _PortInfo:
    def __init__(
        self,
        device: str,
        *,
        description: str = "",
        manufacturer: str = "",
        product: str = "",
        vid: int | None = None,
    ) -> None:
        self.device = device
        self.name = device.rsplit("/", 1)[-1]
        self.description = description
        self.manufacturer = manufacturer
        self.product = product
        self.hwid = ""
        self.vid = vid


def _serial_module(fake_serial: _FakeSerial, ports: list[_PortInfo]):
    return types.SimpleNamespace(
        Serial=lambda *args, **kwargs: fake_serial,
        tools=types.SimpleNamespace(list_ports=types.SimpleNamespace(comports=lambda: ports)),
    )
