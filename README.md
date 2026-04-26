# Circuit-Sensei

Circuit-Sensei is a working prototype of an agentic breadboard assistant for
electronics engineers. The app now runs as a React frontend backed by a FastAPI
server that hosts the agent loop. It takes a circuit goal and component
inventory, creates a breadboard placement plan, draws visual guidance, verifies
each step with Gemini Vision, and then uses an Arduino over USB serial to
stimulate and measure the finished circuit.

The frontend provides the live workbench UI: camera preview, annotated
breadboard image, step list, agent chat, and voice controls. Speech-to-text uses
the browser's built-in Web Speech API, while text-to-speech is proxied through
the backend using the ElevenLabs API.

The project is still mock-friendly: it can run end-to-end without a webcam,
Gemini API key, ElevenLabs API key, or Arduino by starting the backend with
`MOCK_MODE=true`. Real hardware mode uses the same backend, frontend, agent
loop, and tools.

## What It Does

- Accepts a natural-language circuit goal and available component inventory.
- Accepts typed chat or microphone input from the frontend.
- Streams agent messages and session state to the UI over a WebSocket.
- Uses the browser Web Speech API to transcribe microphone input.
- Uses ElevenLabs TTS to speak agent responses.
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
│   ├── server.py
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
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── config.yaml
├── requirements.txt
├── README.md
└── tests/
    ├── test_arduino_tester.py
    ├── test_state_machine.py
    ├── test_tools_mock.py
    └── mock_frame.jpg
```

## Setup

Use Python 3.11 or newer and Node.js 18 or newer.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install the frontend dependencies:

```bash
cd frontend
npm install
```

For real Gemini mode, set `GEMINI_API_KEY`. For ElevenLabs voice output, set
`ELEVENLABS_API_KEY`:

```bash
export GEMINI_API_KEY="your-key"
export ELEVENLABS_API_KEY="your-key"
```

`ELEVENLABS_API_KEY` is optional. Without it, typed chat and browser speech input
still work; the backend returns no audio for TTS. The ElevenLabs voice and TTS
model IDs live in `config.yaml` under `elevenlabs`.

## Run The Web App

Start the backend API server in one terminal:

```bash
source .venv/bin/activate
MOCK_MODE=true uvicorn circuit_sensei.server:app --reload --port 8000
```

Start the frontend dev server in a second terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. Vite proxies frontend `/api` and `/ws` requests to
the FastAPI backend on `http://localhost:8000`, so the browser talks to the
agent through the same host and port as the frontend.

In the web UI:

- Type a goal and inventory in Agent Chat, for example
  `Goal: blink an LED from an Arduino pin. Inventory: Arduino Uno, LED, 330 ohm resistor, jumper wires`.
- Type `next`, `continue`, or `/next` to advance or retry the current state.
- Type `confirm`, `looks good`, or `/confirm` to manually accept the current
  placement when you have checked it yourself.
- Hold the Speak button to use the browser's speech recognition, then forward
  the transcript to the agent.
- Agent responses are sent to ElevenLabs TTS and played in the browser when
  `ELEVENLABS_API_KEY` is set.

While Circuit-Sensei is waiting in `VERIFY`, normal typed text is treated as a
question or note to Gemini and does not advance the step. Use `next` or `/next`
to retry vision verification, or `confirm` or `/confirm` to manually advance
after checking the placement yourself.

After all build steps are verified, `next` moves into a host-controlled Arduino
test. Gemini is no longer allowed to create new breadboard placement steps at
that point, which prevents the workflow from restarting the build plan after the
circuit is already assembled.

## Optional CLI

The original command-line interface is still available for agent-only testing:

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

During a CLI run:

- `/next` advances the state machine.
- `/confirm` manually accepts the current verification step when the webcam or
  Gemini cannot see enough detail but you personally checked the placement.
- `/state` prints the current session state.
- `/quit` exits.

## Real Hardware Mode

Edit `config.yaml`:

```yaml
hardware:
  mock_mode: false
  camera_index: 0
  serial_port: /dev/ttyACM0
  baud_rate: 115200
```

Then start the backend without mock mode:

```bash
source .venv/bin/activate
export GEMINI_API_KEY="your-key"
export ELEVENLABS_API_KEY="your-key"
MOCK_MODE=false uvicorn circuit_sensei.server:app --reload --port 8000
```

Start the frontend with `npm run dev` from `frontend/` as usual.

If `GEMINI_API_KEY` is missing in real mode, the app exits clearly before doing
anything else.

## Webcam And Breadboard Setup

Mount the webcam above the breadboard with a stable top-down view. Keep the
board edges visible and avoid steep perspective angles. The prototype assumes a
single standard breadboard area and maps rows `A-J` across the configured
column range. The current `config.yaml` maps columns `1-30`.

The app writes:

- Raw frame: `/tmp/sensei_frame.jpg`
- Annotated guidance frame: `/tmp/sensei_annotated.jpg`

Test one raw camera capture without starting the agent:

```bash
python -m circuit_sensei.main --real --capture-test
open /tmp/sensei_frame.jpg
```

The capture result prints `brightness` and `enhanced`. On macOS, the default
camera backend is `avfoundation`, with warmup frames enabled so auto-exposure
has time to settle before the frame is saved. If the frame is still dark,
Circuit-Sensei can automatically brighten the saved image before Gemini Vision
sees it.

If webcam capture fails, Circuit-Sensei asks the user to describe the placement
manually instead of advancing blindly.

Optional camera tuning lives in `config.yaml`:

```yaml
camera:
  backend: avfoundation
  warmup_frames: 25
  warmup_delay_seconds: 0.04
  auto_enhance: true
  dark_threshold: 85.0
  target_brightness: 135.0
```

If the image is still dark, increase `warmup_frames` first. If needed, tune
`target_brightness` upward in small steps, such as `150.0`.

## Calibration

Manual calibration lives in `config.yaml`:

```yaml
breadboard:
  image_size: [2162, 1484]
  orientation: standard
  top_left: [1425, 82]
  bottom_right: [1920, 1379]
  row_x_positions: [1425, 1470, 1515, 1560, 1605, 1750, 1790, 1830, 1875, 1920]
  rows: ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
  columns: 30
```

`top_left` and `bottom_right` are pixel coordinates for the usable breadboard
hole grid in the camera or reference image. `row_x_positions` can override the
linear row spacing, which is useful for accounting for the center gap between
the `E` and `F` banks. This is intentionally hackathon-friendly, not a full
computer-vision calibration system.

## Breadboard Topology Rules

Circuit-Sensei models the breadboard terminal strips when creating and checking
plans:

- Holes `A-E` in the same numbered column are electrically connected.
- Holes `F-J` in the same numbered column are electrically connected.
- The center gap separates `E` from `F`.
- One physical hole can hold only one lead or jumper end.
- To connect multiple things to the same node, use different holes in the same
  connected strip, such as `B15` and `C15`.
- A plan that tries to reuse the exact same hole, such as putting two different
  leads into `B15`, is automatically repaired when a free equivalent hole exists.

Example: if `B15` is already occupied, another connection to that same node can
use `C15`, `D15`, `E15`, or `A15`.

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

## Example Web Flow

```text
Open http://localhost:5173

You: Goal: blink an LED from an Arduino pin. Inventory: Arduino Uno, LED, 330 ohm resistor, jumper wires.
Circuit-Sensei: Tell me the circuit goal and available components.

You: next
Circuit-Sensei: Great. I have the goal and inventory. I will derive a compact breadboard plan next.

You: next
Circuit-Sensei: For an LED on 5 V, R = (5 V - about 2 V) / 5-10 mA...
Placement plan:
1. With power disconnected, place the current-limit resistor from A10 to A20.
2. Place the LED anode at E20 and cathode at E25.
3. With Arduino outputs still inactive, connect D9 to column 10 and GND to column 25.

You: next
Circuit-Sensei: With power disconnected, place the current-limit resistor from A10 to A20.
```

The annotated image for that step is saved to `/tmp/sensei_annotated.jpg` and
served to the frontend through `/api/annotated-image`.

## Tests

```bash
pytest
```

Build the frontend before sharing a UI change:

```bash
cd frontend
npm run build
```

The tests exercise the state parser, emergency safety response, mock frame
capture, annotation drawing, breadboard coordinate mapping, and mock Arduino
test path.
