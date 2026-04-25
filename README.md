# Circuit-Sensei

Circuit-Sensei is a working prototype of an agentic breadboard assistant for
electronics engineers. It takes a circuit goal and component inventory, creates
a breadboard placement plan, draws guidance directly on a top-down webcam frame,
uses Gemini Vision to verify each step, and then uses an Arduino over USB serial
to stimulate and measure the finished circuit.

The first version is mock-first: it runs end-to-end without a webcam, Gemini API
key, or Arduino. Real hardware mode uses the same agent loop and tools.

## What It Does

- Accepts a natural-language circuit goal and available component inventory.
- Plans concise breadboard steps using row/column locations such as `A10`.
- Captures a webcam frame to `/tmp/sensei_frame.jpg`.
- Draws highlighted holes, arrows, labels, and step messages onto
  `/tmp/sensei_annotated.jpg`.
- Verifies the captured board image with Gemini Vision before advancing.
- Connects to an Arduino over USB serial after visual verification passes.
- Runs basic tests such as LED drive checks, voltage divider measurements, and
  button reads.

Circuit-Sensei does not use LED strips or physical breadboard guidance LEDs.
All guidance is visual on-screen annotation over the camera image.

## Project Layout

```text
CircuitSensei/
├── circuit_sensei/
│   ├── main.py
│   ├── agent.py
│   ├── tools.py
│   ├── hardware/
│   │   ├── camera.py
│   │   ├── overlay.py
│   │   └── arduino_tester.py
│   ├── prompts/
│   │   └── system_prompt.py
│   └── arduino/
│       └── circuit_tester.ino
├── config.yaml
├── requirements.txt
├── README.md
└── tests/
    ├── test_state_machine.py
    ├── test_tools_mock.py
    └── mock_frame.jpg
```

## Setup

Use Python 3.11 or newer.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For real Gemini mode, set:

```bash
export GEMINI_API_KEY="your-key"
```

## Run In Mock Mode

```bash
python -m circuit_sensei.main --mock
```

Or run a complete mock demo:

```bash
python -m circuit_sensei.main \
  --mock \
  --goal "blink an LED from an Arduino pin" \
  --inventory "Arduino Uno, LED, 330 ohm resistor, jumper wires" \
  --auto-demo
```

During an interactive run:

- `/next` advances the state machine.
- `/confirm` manually accepts the current verification step when the webcam or
  Gemini cannot see enough detail but you personally checked the placement.
- `/state` prints the current session state.
- `/quit` exits.

While Circuit-Sensei is waiting in `VERIFY`, normal typed text is treated as a
question or note to Gemini and does not advance the step. Use `/next` to retry
vision verification, or `/confirm` to manually advance after checking the
placement yourself.

## Real Hardware Mode

Edit `config.yaml`:

```yaml
hardware:
  mock_mode: false
  camera_index: 0
  serial_port: /dev/ttyACM0
  baud_rate: 115200
```

Then run:

```bash
python -m circuit_sensei.main --real
```

If `GEMINI_API_KEY` is missing in real mode, the app exits clearly before doing
anything else.

## Webcam And Breadboard Setup

Mount the webcam above the breadboard with a stable top-down view. Keep the
board edges visible and avoid steep perspective angles. The prototype assumes a
single standard breadboard area and maps rows `A-J` and columns `1-63`.

The app writes:

- Raw frame: `/tmp/sensei_frame.jpg`
- Annotated guidance frame: `/tmp/sensei_annotated.jpg`

If webcam capture fails, Circuit-Sensei asks the user to describe the placement
manually instead of advancing blindly.

## Calibration

Manual calibration lives in `config.yaml`:

```yaml
breadboard:
  image_size: [1280, 720]
  top_left: [110, 95]
  bottom_right: [1170, 615]
  rows: ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
  columns: 63
```

`top_left` and `bottom_right` are pixel coordinates for the usable breadboard
hole grid in the camera image. Circuit-Sensei linearly interpolates approximate
hole positions from those two points. This is intentionally hackathon-friendly,
not a full computer-vision calibration system.

## Arduino Wiring Assumptions

The Arduino remains inactive until the final visual verification passes. When a
test is needed, Circuit-Sensei instructs the user which circuit nodes should
connect to Arduino pins, for example:

- `D9` as a digital or PWM test source.
- `A0` as an analog measurement input.
- `GND` as the common reference.

Do not power a circuit from Arduino outputs until Circuit-Sensei reaches
`VERIFY_COMPLETE`.

## Arduino Serial Protocol

Flash `circuit_sensei/arduino/circuit_tester.ino` to the Arduino. The sketch
uses one JSON-like command per serial line at `115200` baud.

Examples:

```json
{"cmd":"SET_DIGITAL","pin":9,"value":1}
{"cmd":"SET_PWM","pin":9,"value":128}
{"cmd":"READ_DIGITAL","pin":2}
{"cmd":"READ_ANALOG","pin":"A0"}
{"cmd":"RUN_TEST","test_type":"voltage_divider","pin":"A0"}
```

Example response:

```json
{"status":"ok","value":2.480,"unit":"V"}
```

Supported test types in the sketch:

- `voltage_divider`
- `led`
- `button`

## Safety Behavior

If the user mentions smoke, heat, burning, or melting, the app immediately
starts its response with:

```text
⚠️ DISCONNECT POWER NOW
```

## Example Transcript

```text
$ python -m circuit_sensei.main --mock
You: Goal: blink an LED from an Arduino pin
Inventory: Arduino Uno, LED, 330 ohm resistor, jumper wires
Circuit-Sensei: Tell me the circuit goal and available components.

You: /next
Circuit-Sensei: Great. I have the goal and inventory. I will derive a compact breadboard plan next.

You: /next
Circuit-Sensei: For an LED on 5 V, R = (5 V - about 2 V) / 5-10 mA...
Placement plan:
1. With power disconnected, place the current-limit resistor from A10 to A20.
2. Place the LED anode at E20 and cathode at E25.
3. With Arduino outputs still inactive, connect D9 to column 10 and GND to column 25.

You: /next
Circuit-Sensei: With power disconnected, place the current-limit resistor from A10 to A20.
```

The annotated image for that step is saved to `/tmp/sensei_annotated.jpg`.

## Tests

```bash
pytest
```

The tests exercise the state parser, emergency safety response, mock frame
capture, annotation drawing, breadboard coordinate mapping, and mock Arduino
test path.
