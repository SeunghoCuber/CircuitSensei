# Voice Interface Workstream

Branch: `codex/voice-interface`

## Goal

Add a hands-free voice interface so users can talk to Circuit-Sensei during
breadboard assembly and hear responses without constantly using the keyboard.

## Ownership

Primary files/modules to own:

- `circuit_sensei/io/voice.py`
- `circuit_sensei/io/speech_to_text.py`
- `circuit_sensei/io/text_to_speech.py`
- Small, coordinated integration changes in `circuit_sensei/main.py`
- Additive config under `voice:` in `config.yaml`

Avoid editing:

- `circuit_sensei/hardware/overlay.py`
- `circuit_sensei/hardware/camera.py`
- Visual annotation rendering internals

## Interface Contract

Keep the agent interface text-based. Voice should convert audio to text before
calling the agent, and convert agent text to audio after the agent responds.

Suggested boundary:

```python
class VoiceIO:
    def listen(self) -> str:
        ...

    def speak(self, text: str) -> None:
        ...
```

## Requirements

- Preserve existing keyboard CLI behavior.
- Add mock/no-op voice mode so tests and development can run without microphone
  or API access.
- Do not couple voice code to breadboard geometry or annotation internals.
- During `VERIFY`, spoken commands should support equivalents for `/next`,
  `/confirm`, `/state`, and `/quit`.
- Keep provider-specific code behind a small interface so APIs can be swapped.

## Acceptance Checks

```bash
pytest -q
python -m circuit_sensei.main \
  --mock \
  --goal "build a 2.5V voltage divider from a 5V Arduino test source" \
  --inventory "Arduino Uno, two 10k resistors, jumper wires, breadboard" \
  --auto-demo
```

Voice disabled mode should behave exactly like the current CLI.
