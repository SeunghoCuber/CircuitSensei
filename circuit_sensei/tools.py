"""Tool registry used by the Circuit-Sensei agent loop."""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from rich.console import Console
from rich.panel import Panel

from circuit_sensei.hardware.arduino_tester import ArduinoTester, ArduinoUnavailableError
from circuit_sensei.hardware.camera import CameraCapture, camera_settings_from_config, image_size_from_config
from circuit_sensei.hardware.overlay import AnnotationStyle, BreadboardGeometry, FrameAnnotator


@dataclass(frozen=True)
class ToolCall:
    """A model-requested function call."""

    name: str
    args: dict[str, Any]


class GeminiVisionAnalyzer:
    """Small Gemini Vision client used by the analyze_board tool."""

    def __init__(self, model: str, mock_mode: bool, retries: int = 3) -> None:
        self.model = model
        self.mock_mode = mock_mode
        self.retries = retries
        self._client: Any | None = None

    def analyze(self, image_path: str | Path, instruction: str) -> dict[str, Any]:
        """Analyze the current breadboard image for the requested instruction."""

        if self.mock_mode:
            return {
                "ok": True,
                "passed": True,
                "analysis": "Mock vision check passed. The requested placement appears aligned with the annotation.",
                "image_path": str(image_path),
            }

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"ok": False, "passed": False, "analysis": "GEMINI_API_KEY is missing."}

        image = Path(image_path)
        if not image.exists():
            return {"ok": False, "passed": False, "analysis": f"Image not found: {image}"}

        from google import genai  # type: ignore[import-not-found]
        from google.genai import types  # type: ignore[import-not-found]

        if self._client is None:
            self._client = genai.Client(api_key=api_key)

        prompt = (
            "You are verifying a breadboard placement from a top-down webcam image. "
            "Return concise JSON-like text with passed true/false, visible issues, and any safety concern. "
            f"Instruction to verify: {instruction}"
        )
        data = image.read_bytes()
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=[
                        prompt,
                        types.Part.from_bytes(data=data, mime_type="image/jpeg"),
                    ],
                )
                text = getattr(response, "text", "") or ""
                passed = "false" not in text.lower() and "fail" not in text.lower()
                return {"ok": True, "passed": passed, "analysis": text.strip(), "image_path": str(image)}
            except Exception as exc:  # pragma: no cover - external service
                last_error = exc
                time.sleep(0.75 * (2**attempt))
        return {"ok": False, "passed": False, "analysis": f"Gemini Vision failed: {last_error}"}


class CircuitSenseiTools:
    """Implementation of all tools exposed to the Gemini agent."""

    def __init__(self, config: dict[str, Any], console: Console | None = None) -> None:
        self.config = config
        self.console = console or Console()
        hardware = config.get("hardware", {})
        overlay = config.get("overlay", {})
        paths = config.get("paths", {})
        gemini = config.get("gemini", {})

        self.mock_mode = bool(hardware.get("mock_mode", True))
        self.frame_path = str(paths.get("frame_path", "/tmp/sensei_frame.jpg"))
        self.annotated_path = str(paths.get("annotated_path", "/tmp/sensei_annotated.jpg"))
        self.annotation_source = str(overlay.get("annotation_source", "reference")).lower().strip()
        self.reference_image_path = str(overlay.get("reference_image_path", "")).strip()
        self.geometry = BreadboardGeometry.from_config(config)
        self.camera = CameraCapture(
            camera_index=int(hardware.get("camera_index", 0)),
            mock_mode=self.mock_mode,
            settings=camera_settings_from_config(config),
            mock_geometry=self.geometry,
        )
        self.annotator = FrameAnnotator(self.geometry, AnnotationStyle.from_config(config))
        self.arduino = ArduinoTester(
            port=str(hardware.get("serial_port", "/dev/ttyACM0")),
            baud_rate=int(hardware.get("baud_rate", 115200)),
            timeout_seconds=float(hardware.get("serial_timeout_seconds", 2.0)),
            mock_mode=self.mock_mode,
        )
        self.vision = GeminiVisionAnalyzer(
            model=str(gemini.get("vision_model", gemini.get("model", "gemini-2.5-flash"))),
            mock_mode=self.mock_mode,
            retries=int(gemini.get("retries", 3)),
        )

    def execute(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a named tool with clean error handling."""

        args = args or {}
        handlers: dict[str, Callable[..., dict[str, Any]]] = {
            "capture_frame": self.capture_frame,
            "annotate_frame": self.annotate_frame,
            "show_annotated_frame": self.show_annotated_frame,
            "analyze_board": self.analyze_board,
            "arduino_connect": self.arduino_connect,
            "arduino_send_command": self.arduino_send_command,
            "run_test_script": self.run_test_script,
            "alert_user": self.alert_user,
        }
        if name not in handlers:
            return {"ok": False, "error": f"Unknown tool {name!r}"}
        try:
            return handlers[name](**args)
        except ArduinoUnavailableError as exc:
            return {"ok": False, "error": str(exc), "expected_port": self.arduino.port}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "tool": name}

    def capture_frame(self) -> dict[str, Any]:
        """Capture a webcam image and save it to ``/tmp/sensei_frame.jpg``."""

        result = self.camera.capture(self.frame_path, image_size_from_config(self.config))
        return result.__dict__

    @property
    def annotation_uses_camera(self) -> bool:
        """Return whether instruction annotations should use a live camera frame."""

        return self.annotation_source == "camera"

    def prepare_annotation_frame(self) -> dict[str, Any]:
        """Prepare the base image used for instruction annotations."""

        if self.annotation_uses_camera:
            return self.capture_frame()

        frame = Path(self.frame_path)
        source = self.annotation_source
        if self.reference_image_path:
            reference = Path(self.reference_image_path).expanduser()
            if not reference.exists():
                return {
                    "ok": False,
                    "error": f"Reference breadboard image does not exist: {reference}",
                    "path": str(frame),
                    "source": "reference",
                }
            frame.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(reference, frame)
            return {
                "ok": True,
                "path": str(frame),
                "message": "Reference breadboard image loaded.",
                "source": "reference",
                "reference_image_path": str(reference),
            }

        result = self.camera.write_reference_frame(frame, image_size_from_config(self.config))
        data = result.__dict__
        data["source"] = "reference" if source in {"reference", "generated", "static"} else source
        return data

    def annotate_frame(self, annotations: dict[str, Any]) -> dict[str, Any]:
        """Draw breadboard placement guidance on the configured base image."""

        if not self._has_visible_annotation(annotations):
            return {
                "ok": False,
                "error": "No visible annotation data was supplied.",
                "annotations": annotations,
                "annotated_path": self.annotated_path,
            }

        frame = Path(self.frame_path)
        if not frame.exists() or not self.annotation_uses_camera:
            prepared = self.prepare_annotation_frame()
            if not prepared.get("ok"):
                return {
                    "ok": False,
                    "error": prepared.get("error", "Could not prepare annotation frame."),
                    "annotations": annotations,
                    "annotated_path": self.annotated_path,
                    "frame_path": self.frame_path,
                }
        result = self.annotator.annotate(self.frame_path, self.annotated_path, annotations)
        result["annotations"] = annotations
        result["source"] = "camera" if self.annotation_uses_camera else "reference"
        return result

    @staticmethod
    def _has_visible_annotation(annotations: dict[str, Any]) -> bool:
        return bool(
            annotations.get("points")
            or annotations.get("arrows")
            or str(annotations.get("message", "")).strip()
        )

    def show_annotated_frame(self) -> dict[str, Any]:
        """Display or save the annotated frame for the user."""

        path = Path(self.annotated_path)
        if not path.exists():
            return {"ok": False, "error": f"Annotated frame is not available: {path}"}
        self.console.print(Panel(f"Annotated frame saved to {path}", title="Visual Guidance"))
        return {"ok": True, "annotated_path": str(path), "displayed": False}

    def analyze_board(self, instruction: str) -> dict[str, Any]:
        """Send the captured image to Gemini Vision for placement analysis."""

        frame = Path(self.frame_path)
        if not frame.exists():
            capture = self.capture_frame()
            if not capture.get("ok"):
                return {
                    "ok": False,
                    "passed": False,
                    "analysis": "Webcam capture failed. Please describe the board placement manually.",
                }
        return self.vision.analyze(frame, instruction)

    def arduino_connect(self, port: str | None = None) -> dict[str, Any]:
        """Connect to the Arduino USB serial port."""

        return self.arduino.connect(port)

    def arduino_send_command(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a structured JSON command to the Arduino."""

        return self.arduino.send_command(command, params or {})

    def run_test_script(self, test_type: str, expected_values: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a named Arduino test script and return measurements."""

        return self.arduino.run_test_script(test_type, expected_values or {})

    def alert_user(self, message: str, severity: str = "info") -> dict[str, Any]:
        """Print a Rich alert panel."""

        color = {"info": "cyan", "warning": "yellow", "error": "red"}.get(severity, "cyan")
        self.console.print(Panel(message, title=f"Circuit-Sensei {severity.upper()}", border_style=color))
        return {"ok": True, "message": message, "severity": severity}

    def function_declarations(self, state: str | None = None) -> list[dict[str, Any]]:
        """Return Gemini function declarations, optionally filtered by state."""

        declarations = {
            "capture_frame": {
                "name": "capture_frame",
                "description": "Capture a webcam image and save it to /tmp/sensei_frame.jpg.",
                "parameters": {"type": "object", "properties": {}},
            },
            "annotate_frame": {
                "name": "annotate_frame",
                "description": "Draw visual breadboard guidance on the captured frame.",
                "parameters": {
                    "type": "object",
                    "properties": {"annotations": {"type": "object"}},
                    "required": ["annotations"],
                },
            },
            "show_annotated_frame": {
                "name": "show_annotated_frame",
                "description": "Show or save the annotated frame for the user.",
                "parameters": {"type": "object", "properties": {}},
            },
            "analyze_board": {
                "name": "analyze_board",
                "description": "Use Gemini Vision to verify the current breadboard placement.",
                "parameters": {
                    "type": "object",
                    "properties": {"instruction": {"type": "string"}},
                    "required": ["instruction"],
                },
            },
            "arduino_connect": {
                "name": "arduino_connect",
                "description": "Connect to Arduino over USB serial.",
                "parameters": {
                    "type": "object",
                    "properties": {"port": {"type": "string"}},
                },
            },
            "arduino_send_command": {
                "name": "arduino_send_command",
                "description": "Send a JSON command to Arduino.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "params": {"type": "object"},
                    },
                    "required": ["command"],
                },
            },
            "run_test_script": {
                "name": "run_test_script",
                "description": "Run a named Arduino circuit test.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "test_type": {"type": "string"},
                        "expected_values": {"type": "object"},
                    },
                    "required": ["test_type"],
                },
            },
            "alert_user": {
                "name": "alert_user",
                "description": "Print a Rich alert panel.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "severity": {"type": "string"},
                    },
                    "required": ["message"],
                },
            },
        }

        allowed_by_state = {
            "IDLE": ["alert_user"],
            "INTAKE": ["alert_user"],
            "PLAN": ["alert_user"],
            "INSTRUCT": ["annotate_frame", "show_annotated_frame", "alert_user"],
            "VERIFY": ["capture_frame", "analyze_board", "alert_user"],
            "VERIFY_COMPLETE": ["arduino_connect", "alert_user"],
            "TEST": ["arduino_connect", "arduino_send_command", "run_test_script", "alert_user"],
        }
        names = allowed_by_state.get(state or "", list(declarations))
        return [declarations[name] for name in names]

    @staticmethod
    def encode_tool_result(name: str, result: dict[str, Any]) -> str:
        """Return a compact history entry for a completed tool call."""

        return f"TOOL_RESULT {name}: {json.dumps(result, sort_keys=True)}"
