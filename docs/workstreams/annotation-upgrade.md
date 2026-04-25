# Annotation Upgrade Workstream

Branch: `codex/annotation-upgrade`

## Goal

Improve Circuit-Sensei's visual breadboard guidance so captured frames clearly
show where to place components, jumper wires, and Arduino test leads.

## Ownership

Primary files/modules to own:

- `circuit_sensei/hardware/overlay.py`
- `circuit_sensei/hardware/camera.py`
- Focused tests in `tests/test_tools_mock.py`
- Additive config under `camera:` or future `overlay:` sections in
  `config.yaml`

Avoid editing:

- `circuit_sensei/io/*`
- Voice provider code
- Agent state-machine logic except for tiny integration needs agreed with the
  team

## Annotation Contract

Preserve the existing annotation JSON shape so the agent and voice workstreams
do not need to change:

```json
{
  "points": [
    {"row": "A", "col": 10, "label": "R1 leg 1"}
  ],
  "arrows": [
    {
      "from": {"row": "A", "col": 10},
      "to": {"row": "A", "col": 20},
      "label": "place resistor"
    }
  ],
  "message": "Place R1 between A10 and A20."
}
```

## Requirements

- Keep support for highlighted breadboard holes.
- Keep support for arrows between breadboard points.
- Keep support for component labels and step messages.
- Preserve `/tmp/sensei_frame.jpg` and `/tmp/sensei_annotated.jpg` outputs.
- Respect the breadboard topology rules:
  - `A-E` same column are connected.
  - `F-J` same column are connected.
  - `E` and `F` are separated by the center gap.
  - Do not direct two physical leads into the exact same hole.
- Make visual output legible under normal webcam lighting.

## Acceptance Checks

```bash
pytest -q
python -m circuit_sensei.main \
  --mock \
  --goal "build a 2.5V voltage divider from a 5V Arduino test source" \
  --inventory "Arduino Uno, two 10k resistors, jumper wires, breadboard" \
  --auto-demo
open /tmp/sensei_annotated.jpg
```

The generated annotated frame should clearly show target holes, arrows, labels,
and the step message.
