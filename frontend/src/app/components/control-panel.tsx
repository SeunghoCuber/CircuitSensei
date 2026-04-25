import { useRef, useState } from "react";
import { Mic } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

interface ControlPanelProps {
  onSend: (text: string) => void;
}

type RecordingState = "idle" | "recording" | "transcribing";

export function ControlPanel({ onSend }: ControlPanelProps) {
  const [recordingState, setRecordingState] = useState<RecordingState>("idle");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    if (recordingState !== "idle") return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecordingState("recording");
    } catch {
      // microphone denied or unavailable — stay idle
    }
  };

  const stopRecording = () => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    recorder.onstop = async () => {
      setRecordingState("transcribing");
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      recorder.stream.getTracks().forEach((t) => t.stop());
      recorderRef.current = null;
      try {
        const form = new FormData();
        form.append("file", blob, "audio.webm");
        const resp = await fetch("/api/stt", { method: "POST", body: form });
        const data = (await resp.json()) as { text?: string };
        if (data.text?.trim()) onSend(data.text.trim());
      } finally {
        setRecordingState("idle");
      }
    };
    recorder.stop();
  };

  const isRecording = recordingState === "recording";
  const isTranscribing = recordingState === "transcribing";
  const label = isRecording ? "Listening…" : isTranscribing ? "Transcribing…" : "Speak";

  return (
    <Card className="bg-zinc-900 border-zinc-800 p-2">
      <Button
        type="button"
        disabled={isTranscribing}
        onPointerDown={startRecording}
        onPointerUp={stopRecording}
        onPointerLeave={stopRecording}
        onContextMenu={(e) => e.preventDefault()}
        className={`h-12 w-full rounded-lg text-white select-none ${
          isRecording
            ? "bg-red-600 hover:bg-red-700"
            : "bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-900 disabled:text-emerald-100"
        }`}
      >
        <Mic className={`size-5 ${isRecording ? "animate-pulse" : ""}`} />
        <span>{label}</span>
      </Button>
    </Card>
  );
}
