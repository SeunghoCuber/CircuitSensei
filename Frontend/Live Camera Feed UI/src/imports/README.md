# Circuit-Sensei

An agentic breadboard assistant for electronics engineers, powered by Google Gemini.

Circuit-Sensei runs on a host computer, plans a step-by-step breadboard layout,
highlights target positions on a live USB webcam feed, verifies placements with
Gemini Vision, and runs automated electrical tests through an Arduino Uno USB
hardware bridge.

---

## Features

- **Natural language input** - describe your circuit goal in plain English
- **Gemini-powered planning** - calculates component values, shows work
- **OpenCV overlay guidance** - semi-transparent markers with dotted component
  outlines highlight target holes on the live camera view
- **Vision verification** - overhead USB webcam + Gemini Vision checks placements
- **Automated electrical tests** - Arduino Uno signal injection and voltage reads
- **Mock mode** - full pipeline runs on any laptop without hardware

---

## Hardware Wiring

The Python agent runs on your laptop or desktop.  The Arduino Uno connects over
USB and acts purely as the hardware abstraction layer.

```
Arduino Uno
├── Pin 6  → WS2812B LED strip DATA IN
├── Pin 9  → Test signal injection point on breadboard
├── Pin 7  → Digital trigger signal
├── A0     → Circuit output voltage measurement point
├── 5V     → Breadboard power rail (+)
└── GND    → Breadboard power rail (-) + LED strip GND
```

Use a USB webcam mounted above the breadboard for visual verification and the
overlay display.

### LED Strip Power

USB current is limited to about 5V/500mA.  A single WS2812B LED can draw up to
60mA at full white, so 77 LEDs can draw about 4.6A.  Power the full strip from
an external 5V supply and connect the supply ground to Arduino GND.

---

## Arduino Firmware

### Flash the firmware

1. Install Arduino IDE or `arduino-cli`.
2. Install libraries with the Library Manager, or run:

```bash
arduino-cli lib install "Adafruit NeoPixel" "ArduinoJson"
```

3. Compile and upload:

```bash
arduino-cli compile --fqbn arduino:avr:uno firmware/circuit_sensei
arduino-cli upload  --fqbn arduino:avr:uno -p /dev/ttyUSB0 firmware/circuit_sensei
```

### Find the Arduino serial port

Linux/macOS:

```bash
ls /dev/tty* | grep -i usb
```

Windows:

```
Device Manager → Ports (COM & LPT)
```

Common examples are `/dev/ttyUSB0`, `/dev/cu.usbmodem*`, and `COM3`.

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/your-org/circuit-sensei.git
cd circuit-sensei
pip install -r requirements.txt
```

> **Note**: `opencv-python` (not `opencv-python-headless`) is required so that
> `cv2.imshow` can open the overlay display window.

### 2. Set your Gemini API key

Get a free key at https://aistudio.google.com/.

```bash
export GEMINI_API_KEY=your_key_here
```

Add this to your shell profile to persist across sessions.

### 3. Configure `config.yaml`

| Key | Default | Notes |
|-----|---------|-------|
| `mock_mode` | `true` | Set `false` on real hardware |
| `camera.type` | `opencv` | USB webcam backend |
| `camera.device` | `0` | OpenCV VideoCapture index |
| `arduino.port` | `/dev/ttyUSB0` | Use `COM3` on Windows or `/dev/cu.usbmodem*` on macOS |
| `arduino.baud` | `115200` | Must match the firmware |
| `arduino.pwm_signal_pin` | `9` | Test signal injection pin |
| `arduino.voltage_input_pin` | `0` | Analog input A0 for circuit output |
| `arduino.digital_trigger_pin` | `7` | DC trigger pin |
| `display.calibration_file` | `calibration.json` | Path to saved homography |
| `display.marker_radius` | `12` | Overlay circle radius in pixels |
| `display.fps` | `30` | Display window refresh rate |

### 4. First-time camera calibration

On the first real-hardware run, Circuit-Sensei opens a calibration window and
asks you to click the four breadboard corners in this order:

```
1. top-left  (A1)      2. top-right  (A63)
3. bottom-left (J1)    4. bottom-right (J63)
```

The computed perspective matrix is saved to `calibration.json`.  To redo
calibration, delete that file and restart.

### 5. Run

```bash
# Mock mode, no hardware needed:
python main.py

# Real hardware:
python main.py

# Enable debug logging:
python main.py --debug

# Custom config path:
python main.py --config ./config.yaml
```

---

## Viewing the Overlay Window

The overlay window uses `cv2.imshow` on the host computer.  Press `q` inside the
window to exit.

---

## Running in Mock Mode

Set `mock_mode: true` in `config.yaml` (the default).

In mock mode:
- Overlay commands print marker coordinates to stdout instead of drawing
- The display window thread logs `DISPLAY: frame updated` each tick instead of
  calling `cv2.imshow`
- Camera returns `tests/mock_frame.jpg` (generate it first if needed)
- Arduino commands are logged and voltage reads return 2.5V

Generate the mock camera frame once:

```bash
python tests/create_mock_frame.py
```

Then run the full test suite:

```bash
pytest tests/ -v
```

---

## Running Tests

```bash
pytest tests/ -v
pytest tests/test_state_machine.py -v
pytest tests/test_tools_mock.py -v
```

All tests use mocked hardware and mocked Gemini calls.  No API key or physical
hardware is required to run the test suite.

---

## Architecture

```
main.py               CLI REPL + argument parsing
agent.py              AgentSession dataclass, state machine, Gemini tool-call loop
tools.py              Seven tool implementations + FunctionDeclarations + dispatch
display/
  calibration.py      One-time 4-corner click -> perspective transform matrix
  overlay.py          OverlayMarker dataclass + Overlay renderer
  window.py           Background cv2.imshow thread + banner renderer
hardware/
  arduino.py          Host-side JSON-over-serial Arduino interface
  camera.py           OpenCV USB webcam capture (+ mock)
  tester.py           Test runner for tests/circuits/ modules
firmware/
  circuit_sensei/
    circuit_sensei.ino  Arduino Uno firmware
prompts/
  system_prompt.py    Gemini system prompt with state injection
tests/
  test_state_machine.py
  test_tools_mock.py
  circuits/
    low_pass_filter.py
    voltage_divider.py
  create_mock_frame.py
config.yaml           Camera, Arduino, display, and Gemini settings
```

---

## Notes and Caveats

- **Arduino PWM frequency**: `analogWrite` on pin 9 produces a fixed roughly
  490Hz PWM signal.  Swept-frequency tests need a Timer1 firmware extension.
- **Analog input range**: Arduino Uno analog pins read 0-5V with a 10-bit ADC.
  Do not feed A0 more than 5V.
- **Calibration required on first run**: Real hardware needs
  `calibration.json` before overlay markers can be positioned correctly.
- **opencv-python vs opencv-python-headless**: The full `opencv-python` package
  is required because `cv2.imshow` is not available in the headless build.
- **No LangChain / LangGraph**: The agent loop is built directly on the
  `google-genai` Python SDK for transparency and minimal dependencies.

---

## License

MIT -- see LICENSE.
