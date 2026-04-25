import { Cpu, Wifi, PanelRight } from "lucide-react";
import { Button } from "./ui/button";

interface StatusBarProps {
  agentState: string;
  onToggleDrawer: () => void;
}

export function StatusBar({ agentState, onToggleDrawer }: StatusBarProps) {
  return (
    <div className="h-14 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Cpu className="size-5 text-emerald-400" />
          <span className="text-lg">Circuit Sensei</span>
        </div>
        <div className="h-4 w-px bg-zinc-700" />
        <span className="text-sm text-zinc-400">Agentic Breadboard Assistant</span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          <Wifi className="size-4 text-emerald-400" />
          <span className="text-zinc-400">localhost:5173</span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1 bg-zinc-800 rounded-lg text-sm">
          <div className={`size-2 rounded-full ${
            agentState === "idle" ? "bg-zinc-500" :
            agentState === "planning" ? "bg-blue-400 animate-pulse" :
            agentState === "executing" ? "bg-emerald-400 animate-pulse" :
            "bg-yellow-400"
          }`} />
          <span className="capitalize">{agentState}</span>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="border-zinc-700 hover:bg-zinc-800"
          onClick={onToggleDrawer}
        >
          <PanelRight className="size-4 mr-2" />
          Agent Details
        </Button>
      </div>
    </div>
  );
}
