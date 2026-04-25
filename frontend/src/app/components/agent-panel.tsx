import { Brain, CheckCircle2, Clock, Zap, AlertCircle } from "lucide-react";
import { Card } from "./ui/card";

interface AgentPanelProps {
  agentState: string;
}

export function AgentPanel({ agentState }: AgentPanelProps) {
  const mockPlanningSteps = [
    { id: 1, text: "Analyze circuit requirements", status: "completed", voltage: null },
    { id: 2, text: "Calculate resistor values: R1=1kΩ, R2=2.2kΩ", status: "completed", voltage: "3.3V output" },
    { id: 3, text: "Plan breadboard layout (holes A5-A8)", status: "in_progress", voltage: null },
    { id: 4, text: "Verify component placement with vision", status: "pending", voltage: null },
    { id: 5, text: "Run automated electrical tests", status: "pending", voltage: null },
  ];

  const mockTestResults = [
    { name: "Voltage Divider Output", value: "3.28V", expected: "3.3V", status: "pass" },
    { name: "Input Impedance", value: "∞", expected: ">10MΩ", status: "pass" },
    { name: "Signal Integrity", value: "98.2%", expected: ">95%", status: "pass" },
  ];

  return (
    <div className="w-96 flex flex-col gap-4 overflow-y-auto">
      <Card className="bg-zinc-900 border-zinc-800 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Brain className="size-5 text-purple-400" />
          <h2>Agent Status</h2>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-400">Current State</span>
            <span className="text-sm px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded">
              {agentState}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-400">Model</span>
            <span className="text-sm">Gemini Pro</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-400">Hardware Bridge</span>
            <div className="flex items-center gap-1">
              <div className="size-2 bg-emerald-400 rounded-full" />
              <span className="text-sm">Arduino Connected</span>
            </div>
          </div>
        </div>
      </Card>

      <Card className="bg-zinc-900 border-zinc-800 p-4 flex-1">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="size-5 text-yellow-400" />
          <h2>Planning Steps</h2>
        </div>

        <div className="space-y-3">
          {mockPlanningSteps.map((step) => (
            <div key={step.id} className="flex gap-3">
              <div className="mt-0.5">
                {step.status === "completed" && (
                  <CheckCircle2 className="size-4 text-emerald-400" />
                )}
                {step.status === "in_progress" && (
                  <Clock className="size-4 text-blue-400 animate-pulse" />
                )}
                {step.status === "pending" && (
                  <div className="size-4 rounded-full border-2 border-zinc-700" />
                )}
              </div>
              <div className="flex-1 text-sm">
                <div className={step.status === "completed" ? "text-zinc-400" : ""}>
                  {step.text}
                </div>
                {step.voltage && (
                  <div className="text-xs text-emerald-400 mt-1">→ {step.voltage}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="bg-zinc-900 border-zinc-800 p-4">
        <div className="flex items-center gap-2 mb-4">
          <AlertCircle className="size-5 text-blue-400" />
          <h2>Test Results</h2>
        </div>

        <div className="space-y-3">
          {mockTestResults.map((test, idx) => (
            <div key={idx} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-zinc-400">{test.name}</span>
                {test.status === "pass" && (
                  <CheckCircle2 className="size-4 text-emerald-400" />
                )}
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-zinc-500">Measured:</span>
                <span>{test.value}</span>
                <span className="text-zinc-600">|</span>
                <span className="text-zinc-500">Expected:</span>
                <span className="text-zinc-400">{test.expected}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
