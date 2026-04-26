import { useEffect, useRef, useState } from "react";

export interface PlanStep {
  step: number;
  title?: string;
  instruction: string;
  verification?: string;
}

export interface ChatMessage {
  role: "agent" | "user";
  text: string;
}

export interface AgentSocketState {
  connected: boolean;
  isLoading: boolean;
  isSpeaking: boolean;
  ttsEnabled: boolean;
  messages: ChatMessage[];
  agentState: string;
  plan: PlanStep[];
  components: string[];
  currentStep: number;
  verifiedSteps: number[];
  sendMessage: (text: string) => void;
  setTtsEnabled: (enabled: boolean) => void;
}

interface AgentSnapshot {
  current_state?: string;
  placement_plan?: PlanStep[];
  components?: string[];
  current_step?: number;
  verified_steps?: number[];
}

interface AgentSocketMessage {
  type?: string;
  role?: "agent" | "user";
  text?: string;
  state?: string;
  plan?: PlanStep[];
  components?: string[];
  current_step?: number;
  verified_steps?: number[];
  snapshot?: AgentSnapshot;
}

function cleanForSpeech(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/`(.+?)`/g, "$1")
    .trim();
}

export function useAgentSocket(): AgentSocketState {
  const wsRef = useRef<WebSocket | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const ttsEnabledRef = useRef(true);
  const [connected, setConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [ttsEnabledState, setTtsEnabledState] = useState(() => {
    const stored = window.localStorage.getItem("circuit-sensei-tts-enabled");
    return stored === null ? true : stored === "true";
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [agentState, setAgentState] = useState("IDLE");
  const [plan, setPlan] = useState<PlanStep[]>([]);
  const [components, setComponents] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [verifiedSteps, setVerifiedSteps] = useState<number[]>([]);

  const stopCurrentAudio = () => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    setIsSpeaking(false);
  };

  const setTtsEnabled = (enabled: boolean) => {
    ttsEnabledRef.current = enabled;
    setTtsEnabledState(enabled);
    window.localStorage.setItem("circuit-sensei-tts-enabled", String(enabled));
    if (!enabled) {
      stopCurrentAudio();
    }
  };

  const applySessionPayload = (msg: AgentSocketMessage) => {
    const snapshot = msg.snapshot;
    const nextState = msg.state ?? snapshot?.current_state;
    const nextPlan = Array.isArray(msg.plan)
      ? msg.plan
      : Array.isArray(snapshot?.placement_plan)
      ? snapshot.placement_plan
      : undefined;
    const nextComponents = Array.isArray(msg.components)
      ? msg.components
      : Array.isArray(snapshot?.components)
      ? snapshot.components
      : undefined;
    const nextCurrentStep =
      typeof msg.current_step === "number"
        ? msg.current_step
        : typeof snapshot?.current_step === "number"
        ? Math.max(snapshot.current_step - 1, 0)
        : undefined;
    const nextVerifiedSteps = Array.isArray(msg.verified_steps)
      ? msg.verified_steps
      : Array.isArray(snapshot?.verified_steps)
      ? snapshot.verified_steps
      : undefined;

    if (nextState) setAgentState(nextState);
    if (nextPlan !== undefined) setPlan(nextPlan);
    if (nextComponents !== undefined) setComponents(nextComponents);
    if (nextCurrentStep !== undefined) setCurrentStep(nextCurrentStep);
    if (nextVerifiedSteps !== undefined) setVerifiedSteps(nextVerifiedSteps);
  };

  const speakText = async (text: string) => {
    if (!ttsEnabledRef.current) return;

    const clean = cleanForSpeech(text);
    if (!clean) return;

    // Stop any currently playing audio
    stopCurrentAudio();

    try {
      setIsSpeaking(true);
      const resp = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: clean }),
      });
      if (!resp.ok) {
        setIsSpeaking(false);
        return;
      }
      const blob = await resp.blob();
      if (!ttsEnabledRef.current) {
        setIsSpeaking(false);
        return;
      }
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      currentAudioRef.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        currentAudioRef.current = null;
        setIsSpeaking(false);
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        currentAudioRef.current = null;
        setIsSpeaking(false);
      };
      await audio.play();
    } catch {
      setIsSpeaking(false);
    }
  };

  useEffect(() => {
    ttsEnabledRef.current = ttsEnabledState;
  }, [ttsEnabledState]);

  useEffect(() => {
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${location.host}/ws`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string) as AgentSocketMessage;

        if ((msg.type === "message" || msg.type === "progress") && msg.role === "agent") {
          const text = msg.text ?? "";
          setMessages((prev) => [...prev, { role: "agent", text }]);
          speakText(text);
          if (msg.type === "message") {
            setIsLoading(false);
          }
        }

        if (
          msg.type === "message" ||
          msg.type === "progress" ||
          msg.type === "connected" ||
          msg.type === "state"
        ) {
          applySessionPayload(msg);
        }
      } catch {
        // ignore malformed frames
      }
    };

    return () => {
      ws.close();
      stopCurrentAudio();
    };
    // speakText only uses refs and stable setters — safe to omit from deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sendMessage = (text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    const command = text.trim().toLowerCase();
    // Don't echo slash commands as user messages in the chat
    if (command !== "/next" && command !== "/state") {
      setMessages((prev) => [...prev, { role: "user", text }]);
    }
    setIsLoading(true);
    wsRef.current.send(JSON.stringify({ type: "message", text }));
  };

  return {
    connected,
    isLoading,
    isSpeaking,
    ttsEnabled: ttsEnabledState,
    messages,
    sendMessage,
    setTtsEnabled,
    agentState,
    plan,
    components,
    currentStep,
    verifiedSteps,
  };
}
