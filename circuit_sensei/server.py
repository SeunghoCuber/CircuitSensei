"""FastAPI server bridging the Circuit-Sensei agent to the React frontend."""

from __future__ import annotations

import asyncio
import json
import os
import random
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from circuit_sensei.agent import AgentSession, CircuitSenseiAgent, SessionState, create_model_client
from circuit_sensei.hardware.arduino_tester import normalize_serial_port
from circuit_sensei.hardware.camera import image_size_from_config
from circuit_sensei.hardware.overlay import BreadboardGeometry
from circuit_sensei.tools import CircuitSenseiTools, config_bool


def _load_config() -> dict[str, Any]:
    path = os.environ.get("CONFIG_PATH") or str(Path(__file__).parent.parent / "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return dict(yaml.safe_load(f) or {})


def _build_agent(config: dict[str, Any]) -> tuple[AgentSession, CircuitSenseiAgent]:
    geometry = BreadboardGeometry.from_config(config)
    session = AgentSession(
        breadboard_geometry={
            "top_left": geometry.top_left,
            "bottom_right": geometry.bottom_right,
            "rows": geometry.rows,
            "columns": geometry.columns,
        },
        arduino_port=normalize_serial_port(config.get("hardware", {}).get("serial_port")),
    )
    tools = CircuitSenseiTools(config)
    model_client = create_model_client(config)
    agent = CircuitSenseiAgent(
        session=session,
        tools=tools,
        model_client=model_client,
        max_tool_rounds=int(config.get("gemini", {}).get("max_tool_rounds", 6)),
    )
    return session, agent


config = _load_config()
config.setdefault("hardware", {})
# Allow env var to override config.yaml; otherwise config.yaml is authoritative
if "MOCK_MODE" in os.environ:
    config["hardware"]["mock_mode"] = config_bool(
        os.environ["MOCK_MODE"],
        default=config_bool(config["hardware"].get("mock_mode"), default=True),
    )

ANNOTATED_PATH: str = config.get("paths", {}).get("annotated_path", "/tmp/sensei_annotated.jpg")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_PATH: str = str(PROJECT_ROOT / "arduino_uno.png")

VERIFY_START_PHRASES: tuple[str, ...] = (
    "Okay, give me a second to verify this step with the camera, then we can move on.",
    "Great, I am running the visual verification now. This will take a moment.",
    "Thanks. Let me quickly check this placement with Gemini Vision.",
    "Perfect, starting the camera check now. I will confirm as soon as it finishes.",
    "All right, I am validating this step now. Hang tight for a few seconds.",
)

AVAILABLE_MODELS: list[str] = ["gemini-2.5-flash", "gemini-3-flash-preview", "gemma-4-31b-it"]

ELEVENLABS_API_KEY: str = os.environ.get("ELEVENLABS_API_KEY", "")
_el_cfg = config.get("elevenlabs", {})
ELEVENLABS_VOICE_ID: str = str(_el_cfg.get("voice_id", "JBFqnCBsd6RMkjVDRZzb"))
ELEVENLABS_TTS_MODEL: str = str(_el_cfg.get("tts_model", "eleven_turbo_v2_5"))

session, agent = _build_agent(config)

app = FastAPI(title="Circuit-Sensei API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _clear_stale_annotation_on_startup() -> None:
    """Clear stale guidance from older runs before the first user step."""

    Path(ANNOTATED_PATH).unlink(missing_ok=True)


def _read_image(path: str) -> Response | None:
    if os.path.exists(path):
        media_type = "image/png" if path.lower().endswith(".png") else "image/jpeg"
        with open(path, "rb") as f:
            data = f.read()
        return Response(
            content=data,
            media_type=media_type,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"},
        )
    return None


def _latest_annotation_step() -> int | None:
    """Return the step number for the most recent successful annotation."""

    prefix = "TOOL_RESULT annotate_frame: "
    for entry in reversed(session.conversation_history):
        if entry.get("role") != "tool" or entry.get("name") != "annotate_frame":
            continue
        content = str(entry.get("content", ""))
        if not content.startswith(prefix):
            continue
        try:
            payload = json.loads(content[len(prefix):])
        except json.JSONDecodeError:
            continue
        if not payload.get("ok"):
            continue
        annotations = payload.get("annotations")
        if not isinstance(annotations, dict):
            continue
        try:
            return int(annotations["step"])
        except (KeyError, TypeError, ValueError):
            return None
    return None


def _annotation_matches_current_step(requested_step: int | None = None) -> bool:
    if not session.placement_plan:
        return False
    current_step = session.current_step + 1
    if requested_step is not None and requested_step != current_step:
        return False
    return _latest_annotation_step() == current_step


def _frontend_session_payload() -> dict[str, Any]:
    """Return the session fields the React app consumes directly."""

    return {
        "state": session.current_state.value,
        "plan": session.placement_plan,
        "components": session.components,
        "current_step": session.current_step,
        "verified_steps": session.verified_steps,
        "mock_mode": agent.tools.mock_mode,
        "vision_mock_mode": agent.tools.vision.mock_mode,
    }


def _verification_start_phrase() -> str:
    """Return a short spoken progress message before VERIFY analysis runs."""

    return random.choice(VERIFY_START_PHRASES)


@app.get("/api/reference-image")
async def get_reference_image() -> Response:
    """Serve the plain unannotated breadboard image."""
    resp = _read_image(REFERENCE_PATH)
    if resp:
        return resp
    return Response(status_code=404)


@app.get("/api/annotated-image")
async def get_annotated_image(step: int | None = Query(default=None)) -> Response:
    """Serve the latest annotated breadboard guidance image."""
    if not _annotation_matches_current_step(step):
        return Response(status_code=404)
    resp = _read_image(ANNOTATED_PATH)
    if resp:
        return resp
    return Response(status_code=404)


@app.get("/api/state")
async def get_state() -> dict[str, Any]:
    """Return a snapshot of the current agent session state."""
    return {
        **session.snapshot(),
        "mock_mode": agent.tools.mock_mode,
        "vision_mock_mode": agent.tools.vision.mock_mode,
    }


@app.post("/api/tts")
async def text_to_speech(request: Request) -> Response:
    """Proxy text to ElevenLabs TTS and return audio/mpeg."""
    if not ELEVENLABS_API_KEY:
        return Response(status_code=204)
    body = await request.json()
    text = str(body.get("text", "")).strip()
    if not text:
        return Response(status_code=204)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={"text": text, "model_id": ELEVENLABS_TTS_MODEL},
        )
    if resp.status_code != 200:
        return Response(status_code=resp.status_code)
    return Response(content=resp.content, media_type="audio/mpeg")


@app.get("/api/model")
async def get_model() -> dict[str, Any]:
    """Return the currently active LLM model name."""
    return {"model": config.get("gemini", {}).get("model", AVAILABLE_MODELS[0])}


@app.post("/api/model")
async def set_model(request: Request) -> dict[str, Any]:
    """Switch the active LLM model; rebuilds the model client immediately."""
    body = await request.json()
    model_name = str(body.get("model", ""))
    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_name!r}")
    config.setdefault("gemini", {})["model"] = model_name
    agent.model_client = create_model_client(config)
    return {"model": model_name}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Bidirectional WebSocket for agent chat messages."""
    await websocket.accept()

    # Send initial connection message with current state
    await websocket.send_text(json.dumps({
        "type": "connected",
        **_frontend_session_payload(),
    }))

    loop = asyncio.get_event_loop()
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg.get("type") != "message":
                continue

            user_text: str = msg.get("text", "")
            command = user_text.strip().lower().rstrip(".,!?;:")

            # Natural-language proceed phrases that always mean "continue/retry"
            _PROCEED = {
                "/next", "next", "continue", "proceed", "go ahead",
                "ready", "retry", "try again", "check again", "re-check", "recheck",
            }

            if command in _PROCEED:
                user_text = ""
            elif command in {"/confirm", "confirm", "confirmed", "manual confirm", "manually confirm",
                             "looks good", "it looks good", "looks correct", "it looks correct",
                             "all good", "it's good", "its good", "i checked", "i checked it",
                             "i verified", "i verified it", "it's correct", "its correct",
                             "it's right", "its right", "skip vision", "trust me"}:
                response = await loop.run_in_executor(None, agent.manual_confirm_current_step)
                await websocket.send_text(json.dumps({
                    "type": "message",
                    "role": "agent",
                    "text": response,
                    "image_updated": _annotation_matches_current_step(),
                    **_frontend_session_payload(),
                }))
                continue
            elif command == "/state":
                await websocket.send_text(json.dumps({
                    "type": "state",
                    "snapshot": session.snapshot(),
                    **_frontend_session_payload(),
                }))
                continue

            should_emit_verify_progress = (
                session.current_state == SessionState.VERIFY and not user_text.strip()
            )
            if should_emit_verify_progress:
                await websocket.send_text(json.dumps({
                    "type": "progress",
                    "role": "agent",
                    "text": _verification_start_phrase(),
                    "image_updated": _annotation_matches_current_step(),
                    **_frontend_session_payload(),
                }))

            # Run the blocking agent call in a thread pool
            response: str = await loop.run_in_executor(
                None, agent.handle_user_message, user_text
            )

            await websocket.send_text(json.dumps({
                "type": "message",
                "role": "agent",
                "text": response,
                "image_updated": _annotation_matches_current_step(),
                **_frontend_session_payload(),
            }))

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "text": str(exc),
            }))
        except Exception:
            pass
