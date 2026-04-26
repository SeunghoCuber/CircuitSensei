import { useEffect, useRef, useState } from "react";
import { MessageCircle, Send, Volume2, VolumeX } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";
import type { ChatMessage } from "../hooks/use-agent-socket";

const AVAILABLE_MODELS = ["gemini-2.5-flash", "gemini-3-flash-preview", "gemma-4-31b-it"] as const;
type ModelId = typeof AVAILABLE_MODELS[number];

const MODEL_LABELS: Record<ModelId, string> = {
  "gemini-2.5-flash": "2.5 Flash",
  "gemini-3-flash-preview": "3 Flash Preview",
  "gemma-4-31b-it": "Gemma 4",
};

interface DisplayMessage {
  role: "agent" | "user";
  text: string;
  streaming: boolean;
}

interface CameraViewProps {
  messages: ChatMessage[];
  isLoading: boolean;
  ttsEnabled: boolean;
  onTtsEnabledChange: (enabled: boolean) => void;
  onSend: (text: string) => void;
}

function renderBold(text: string) {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return parts.map((part, i) =>
    i % 2 === 1 ? <strong key={i} className="font-semibold">{part}</strong> : part
  );
}

export function CameraView({
  messages,
  isLoading,
  ttsEnabled,
  onTtsEnabledChange,
  onSend,
}: CameraViewProps) {
  const [inputText, setInputText] = useState("");
  const [displayed, setDisplayed] = useState<DisplayMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const processedRef = useRef(0);
  const [selectedModel, setSelectedModel] = useState<ModelId>("gemma-4-31b-it");

  useEffect(() => {
    fetch("/api/model")
      .then((r) => r.json())
      .then((data) => {
        if (AVAILABLE_MODELS.includes(data.model)) setSelectedModel(data.model as ModelId);
      })
      .catch(() => {});
  }, []);

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const model = e.target.value as ModelId;
    setSelectedModel(model);
    fetch("/api/model", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    }).catch(() => {});
  };

  // Typewriter effect: process new messages as they arrive
  useEffect(() => {
    if (messages.length <= processedRef.current) return;

    const incoming = messages.slice(processedRef.current);
    processedRef.current = messages.length;

    for (const msg of incoming) {
      if (msg.role === "user") {
        setDisplayed((prev) => [...prev, { role: "user", text: msg.text, streaming: false }]);
        continue;
      }

      // Agent message: add empty entry then stream characters in
      const fullText = msg.text;
      setDisplayed((prev) => [...prev, { role: "agent", text: "", streaming: true }]);

      let i = 0;
      const timer = setInterval(() => {
        i = Math.min(i + 4, fullText.length);
        setDisplayed((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.streaming) {
            next[next.length - 1] = {
              ...last,
              text: fullText.slice(0, i),
              streaming: i < fullText.length,
            };
          }
          return next;
        });
        if (i >= fullText.length) clearInterval(timer);
      }, 14);
    }
  }, [messages]);

  // Scroll to bottom whenever displayed messages or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayed, isLoading]);

  const handleSubmit = (e: { preventDefault(): void }) => {
    e.preventDefault();
    const text = inputText.trim();
    if (!text) return;
    onSend(text);
    setInputText("");
  };

  return (
    <Card className="w-80 bg-zinc-900 border-zinc-800 p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <MessageCircle className="size-4 text-emerald-400" />
          <span className="text-sm text-zinc-100">Agent Chat</span>
          <span className="text-zinc-600 text-xs select-none">·</span>
          <select
            value={selectedModel}
            onChange={handleModelChange}
            className="text-xs text-zinc-400 bg-transparent border-none outline-none cursor-pointer hover:text-zinc-200 focus:text-zinc-200 transition-colors appearance-none"
          >
            {AVAILABLE_MODELS.map((m) => (
              <option key={m} value={m} className="bg-zinc-900 text-zinc-200">{MODEL_LABELS[m]}</option>
            ))}
          </select>
        </div>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={ttsEnabled ? "Turn off text to speech" : "Turn on text to speech"}
              aria-pressed={ttsEnabled}
              onClick={() => onTtsEnabledChange(!ttsEnabled)}
              className={`size-8 shrink-0 hover:bg-zinc-800 ${
                ttsEnabled ? "text-emerald-400" : "text-zinc-500"
              }`}
            >
              {ttsEnabled ? <Volume2 className="size-4" /> : <VolumeX className="size-4" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left">
            {ttsEnabled ? "Turn off TTS" : "Turn on TTS"}
          </TooltipContent>
        </Tooltip>
      </div>

      <div className="flex-1 flex flex-col min-h-0 gap-3">
        <div className="flex-1 overflow-y-auto no-scrollbar space-y-2 pr-1">
          {displayed.length === 0 && !isLoading && (
            <div className="text-xs text-zinc-600 text-center py-10">
              Tell the agent your goal to get started.
            </div>
          )}

          {displayed.map((msg, i) => (
            <div
              key={i}
              className={`rounded-lg px-3 py-2 text-sm leading-relaxed ${
                msg.role === "agent"
                  ? "bg-zinc-800 text-zinc-100"
                  : "bg-emerald-600 text-white ml-8"
              }`}
            >
              {renderBold(msg.text)}
              {msg.role === "agent" && msg.streaming && (
                <span className="inline-block w-0.5 h-3.5 bg-zinc-400 ml-0.5 align-middle animate-pulse" />
              )}
            </div>
          ))}

          {/* Loading dots while waiting for agent response */}
          {isLoading && (
            <div className="bg-zinc-800 rounded-lg px-3 py-3 flex gap-1.5 items-center w-fit">
              <span className="size-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:0ms]" />
              <span className="size-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:150ms]" />
              <span className="size-1.5 rounded-full bg-zinc-400 animate-bounce [animation-delay:300ms]" />
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Message agent…"
            className="min-w-0 flex-1 bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <Button type="submit" size="icon" className="bg-emerald-600 hover:bg-emerald-700 shrink-0">
            <Send className="size-4" />
          </Button>
        </form>
      </div>
    </Card>
  );
}
