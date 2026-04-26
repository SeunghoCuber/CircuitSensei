import { useEffect, useRef, useState } from "react";
import { Mic } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

interface ControlPanelProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

type RecognitionState = "idle" | "listening" | "processing" | "unsupported";

interface BrowserSpeechRecognitionAlternative {
  transcript: string;
}

interface BrowserSpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly [index: number]: BrowserSpeechRecognitionAlternative | undefined;
}

interface BrowserSpeechRecognitionResultList {
  readonly length: number;
  readonly [index: number]: BrowserSpeechRecognitionResult | undefined;
}

interface BrowserSpeechRecognitionEvent {
  readonly resultIndex: number;
  readonly results: BrowserSpeechRecognitionResultList;
}

interface BrowserSpeechRecognitionErrorEvent {
  readonly error?: string;
}

interface BrowserSpeechRecognition {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onend: (() => void) | null;
  onerror: ((event: BrowserSpeechRecognitionErrorEvent) => void) | null;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null;
  abort: () => void;
  start: () => void;
  stop: () => void;
}

type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition;
type SpeechRecognitionWindow = Window &
  typeof globalThis & {
    SpeechRecognition?: BrowserSpeechRecognitionConstructor;
    webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor;
  };

function getSpeechRecognitionConstructor(): BrowserSpeechRecognitionConstructor | null {
  const speechWindow = window as SpeechRecognitionWindow;
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition ?? null;
}

function normalizeTranscript(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

export function ControlPanel({ onSend, disabled = false }: ControlPanelProps) {
  const [recognitionState, setRecognitionState] = useState<RecognitionState>(() =>
    getSpeechRecognitionConstructor() ? "idle" : "unsupported",
  );
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const finalTranscriptRef = useRef("");
  const interimTranscriptRef = useRef("");

  useEffect(() => {
    return () => {
      const recognition = recognitionRef.current;
      if (recognition) {
        recognition.onend = null;
        recognition.onerror = null;
        recognition.onresult = null;
        recognition.abort();
      }
      recognitionRef.current = null;
    };
  }, []);

  const startListening = () => {
    if (disabled) return;
    if (recognitionState !== "idle") return;

    const SpeechRecognition = getSpeechRecognitionConstructor();
    if (!SpeechRecognition) {
      setRecognitionState("unsupported");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      finalTranscriptRef.current = "";
      interimTranscriptRef.current = "";

      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = navigator.language || "en-US";
      recognition.maxAlternatives = 1;

      recognition.onresult = (event) => {
        let nextFinal = finalTranscriptRef.current;
        let nextInterim = "";

        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const result = event.results[i];
          const transcript = result?.[0]?.transcript ?? "";

          if (result?.isFinal) {
            nextFinal = `${nextFinal} ${transcript}`;
          } else {
            nextInterim = `${nextInterim} ${transcript}`;
          }
        }

        finalTranscriptRef.current = nextFinal;
        interimTranscriptRef.current = nextInterim;
      };

      recognition.onerror = (event) => {
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          recognitionRef.current = null;
          setRecognitionState("idle");
        }
      };

      recognition.onend = () => {
        const transcript = normalizeTranscript(
          `${finalTranscriptRef.current} ${interimTranscriptRef.current}`,
        );

        recognitionRef.current = null;
        finalTranscriptRef.current = "";
        interimTranscriptRef.current = "";
        setRecognitionState("idle");

        if (transcript) {
          onSend(transcript);
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
      setRecognitionState("listening");
    } catch {
      recognitionRef.current = null;
      setRecognitionState("idle");
    }
  };

  const stopListening = () => {
    const recognition = recognitionRef.current;
    if (!recognition || recognitionState !== "listening") return;

    setRecognitionState("processing");
    try {
      recognition.stop();
    } catch {
      recognitionRef.current = null;
      setRecognitionState("idle");
    }
  };

  const isListening = recognitionState === "listening";
  const isProcessing = recognitionState === "processing";
  const isUnsupported = recognitionState === "unsupported";
  const label = isListening
    ? "Listening..."
    : isProcessing
    ? "Processing..."
    : disabled
    ? "Demo complete"
    : isUnsupported
    ? "Speech unavailable"
    : "Speak";

  return (
    <Card className="bg-zinc-900 border-zinc-800 p-2">
      <Button
        type="button"
        disabled={disabled || isProcessing || isUnsupported}
        onPointerDown={startListening}
        onPointerUp={stopListening}
        onPointerLeave={stopListening}
        onPointerCancel={stopListening}
        onContextMenu={(e) => e.preventDefault()}
        className={`h-12 w-full rounded-lg text-white select-none ${
          isListening
            ? "bg-red-600 hover:bg-red-700"
            : "bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-900 disabled:text-emerald-100"
        }`}
      >
        <Mic className={`size-5 ${isListening ? "animate-pulse" : ""}`} />
        <span>{label}</span>
      </Button>
    </Card>
  );
}
