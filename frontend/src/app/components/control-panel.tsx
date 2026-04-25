import { useState } from "react";
import { Send, PlayCircle, StopCircle, RotateCcw } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

interface ControlPanelProps {
  onStateChange: (state: string) => void;
  onConnectionsUpdate: (connections: Array<{
    id: string;
    from: string;
    to: string;
    component?: string;
    color?: string;
  }>) => void;
  onStepChange: (step: number) => void;
}

export function ControlPanel({ onStateChange, onConnectionsUpdate, onStepChange }: ControlPanelProps) {
  const [input, setInput] = useState("");
  const [isRunning, setIsRunning] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    onStateChange("planning");
    setIsRunning(true);

    const mockConnections = [
      { id: "r1-1", from: "A5", to: "A10", component: "1kΩ Resistor", color: "#10b981" },
      { id: "r1-2", from: "A10", to: "A15", component: "2.2kΩ Resistor", color: "#10b981" },
      { id: "wire-1", from: "A5", to: "Power", component: "Red Wire", color: "#ef4444" },
      { id: "wire-2", from: "A15", to: "Ground", component: "Black Wire", color: "#000000" },
    ];

    setTimeout(() => {
      onConnectionsUpdate(mockConnections);
      onStateChange("executing");
      onStepChange(0);
    }, 1500);

    setInput("");
  };

  const handleStop = () => {
    setIsRunning(false);
    onStateChange("idle");
    onConnectionsUpdate([]);
    onStepChange(0);
  };

  const handleReset = () => {
    setIsRunning(false);
    onStateChange("idle");
    onConnectionsUpdate([]);
    onStepChange(0);
    setInput("");
  };

  return (
    <Card className="bg-zinc-900 border-zinc-800 p-4">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="What would you like to build? (e.g., voltage divider, LED circuit, sensor circuit...)"
            className="flex-1 bg-zinc-950 border border-zinc-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 placeholder:text-zinc-600"
            disabled={isRunning}
          />
          <Button
            type="submit"
            disabled={isRunning || !input.trim()}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            <Send className="size-4 mr-2" />
            Start Building
          </Button>
        </div>

        <div className="flex gap-2">
          {!isRunning ? (
            <Button
              type="button"
              variant="outline"
              className="flex-1 border-zinc-700 hover:bg-zinc-800"
              onClick={() => {
                setInput("Build a voltage divider that outputs 3.3V from 5V input");
              }}
            >
              <PlayCircle className="size-4 mr-2" />
              Example: Voltage Divider
            </Button>
          ) : (
            <Button
              type="button"
              variant="outline"
              className="flex-1 border-red-700 text-red-400 hover:bg-red-950"
              onClick={handleStop}
            >
              <StopCircle className="size-4 mr-2" />
              Stop
            </Button>
          )}

          <Button
            type="button"
            variant="outline"
            className="border-zinc-700 hover:bg-zinc-800"
            onClick={handleReset}
          >
            <RotateCcw className="size-4" />
          </Button>
        </div>
      </form>
    </Card>
  );
}
