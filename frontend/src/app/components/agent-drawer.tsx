import { X, Brain, Zap, Activity, CheckCircle2 } from "lucide-react";
import { Button } from "./ui/button";

interface AgentDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  agentState: string;
}

export function AgentDrawer({ isOpen, onClose, agentState }: AgentDrawerProps) {
  const planningSteps = [
    { text: "Parse user requirements", status: "completed" },
    { text: "Calculate component values: R1=1kΩ, R2=2.2kΩ", status: "completed" },
    { text: "Design breadboard layout (optimized)", status: "completed" },
    { text: "Generate step-by-step assembly instructions", status: "in_progress" },
    { text: "Prepare verification checkpoints", status: "pending" },
  ];

  const testResults = [
    { name: "Component Detection", value: "5/5 detected", status: "pass" },
    { name: "Placement Accuracy", value: "±0.5mm", status: "pass" },
    { name: "Wire Routing", value: "Optimal", status: "pass" },
  ];

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          onClick={onClose}
        />
      )}

      <div
        className={`fixed right-0 top-0 h-full w-96 bg-zinc-900 border-l border-zinc-800 shadow-2xl transform transition-transform duration-300 z-50 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-between p-4 border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <Brain className="size-5 text-purple-400" />
              <h2>Agent Details</h2>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="hover:bg-zinc-800"
            >
              <X className="size-4" />
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Activity className="size-4 text-blue-400" />
                <h3 className="text-sm">System Status</h3>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Agent State</span>
                  <span className="capitalize text-emerald-400">{agentState}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Model</span>
                  <span>Gemini Pro</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Arduino Bridge</span>
                  <div className="flex items-center gap-1">
                    <div className="size-2 bg-emerald-400 rounded-full" />
                    <span className="text-xs">Connected</span>
                  </div>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Camera</span>
                  <div className="flex items-center gap-1">
                    <div className="size-2 bg-emerald-400 rounded-full" />
                    <span className="text-xs">Active</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="size-4 text-yellow-400" />
                <h3 className="text-sm">Planning Pipeline</h3>
              </div>

              <div className="space-y-2">
                {planningSteps.map((step, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <div className="mt-0.5">
                      {step.status === "completed" && (
                        <CheckCircle2 className="size-3.5 text-emerald-400" />
                      )}
                      {step.status === "in_progress" && (
                        <div className="size-3.5 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
                      )}
                      {step.status === "pending" && (
                        <div className="size-3.5 rounded-full border-2 border-zinc-700" />
                      )}
                    </div>
                    <div className="text-xs text-zinc-400">{step.text}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="size-4 text-emerald-400" />
                <h3 className="text-sm">Vision Verification</h3>
              </div>

              <div className="space-y-2">
                {testResults.map((test, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs">
                    <span className="text-zinc-400">{test.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-zinc-300">{test.value}</span>
                      <CheckCircle2 className="size-3 text-emerald-400" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
              <h3 className="text-sm mb-2">Calculated Values</h3>
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between text-zinc-400">
                  <span>R1 (top resistor)</span>
                  <span className="text-emerald-400">1.0 kΩ</span>
                </div>
                <div className="flex justify-between text-zinc-400">
                  <span>R2 (bottom resistor)</span>
                  <span className="text-emerald-400">2.2 kΩ</span>
                </div>
                <div className="flex justify-between text-zinc-400">
                  <span>Expected V_out</span>
                  <span className="text-yellow-400">3.28 V</span>
                </div>
                <div className="flex justify-between text-zinc-400">
                  <span>Total current</span>
                  <span className="text-blue-400">1.56 mA</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
