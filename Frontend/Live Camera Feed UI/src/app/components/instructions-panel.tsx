import { CheckCircle2, Circle, ChevronRight } from "lucide-react";
import { Card } from "./ui/card";
import { Button } from "./ui/button";

interface InstructionsPanelProps {
  currentStep: number;
  onStepChange: (step: number) => void;
  agentState: string;
}

export function InstructionsPanel({ currentStep, onStepChange, agentState }: InstructionsPanelProps) {
  const instructions = [
    {
      id: 1,
      title: "Place 1kΩ Resistor (R1)",
      details: "Connect from A5 to A10",
      component: "Brown-Black-Red resistor",
      completed: currentStep > 0,
    },
    {
      id: 2,
      title: "Place 2.2kΩ Resistor (R2)",
      details: "Connect from A10 to A15",
      component: "Red-Red-Red resistor",
      completed: currentStep > 1,
    },
    {
      id: 3,
      title: "Connect Power Rail",
      details: "Red wire from + rail to A5",
      component: "Use red jumper wire",
      completed: currentStep > 2,
    },
    {
      id: 4,
      title: "Connect Ground",
      details: "Black wire from A15 to - rail",
      component: "Use black jumper wire",
      completed: currentStep > 3,
    },
    {
      id: 5,
      title: "Add Output Probe",
      details: "Yellow wire from A10 to Arduino A0",
      component: "Measurement point at junction",
      completed: currentStep > 4,
    },
  ];

  const currentInstruction = instructions[currentStep];

  return (
    <Card className="w-96 bg-zinc-900 border-zinc-800 p-4 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2>Assembly Instructions</h2>
        <span className="text-sm text-zinc-400">
          Step {currentStep + 1} of {instructions.length}
        </span>
      </div>

      {currentInstruction && (
        <div className="mb-4 p-4 bg-emerald-950/30 border border-emerald-900 rounded-lg">
          <div className="flex items-start gap-3">
            <div className="mt-1">
              <div className="size-8 rounded-full bg-emerald-500 flex items-center justify-center text-zinc-900">
                {currentStep + 1}
              </div>
            </div>
            <div className="flex-1">
              <h3 className="text-emerald-400 mb-1">{currentInstruction.title}</h3>
              <p className="text-sm text-zinc-300 mb-2">{currentInstruction.details}</p>
              <p className="text-xs text-zinc-500">{currentInstruction.component}</p>
            </div>
          </div>

          {currentStep < instructions.length - 1 && (
            <Button
              className="w-full mt-4 bg-emerald-600 hover:bg-emerald-700"
              onClick={() => onStepChange(currentStep + 1)}
            >
              Mark Complete & Continue
              <ChevronRight className="size-4 ml-2" />
            </Button>
          )}

          {currentStep === instructions.length - 1 && (
            <div className="mt-4 p-3 bg-emerald-900/30 rounded text-sm text-emerald-300 text-center">
              Assembly complete! Ready for testing.
            </div>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-2">
        <div className="text-xs text-zinc-500 mb-2">All Steps</div>
        {instructions.map((instruction, idx) => (
          <div
            key={instruction.id}
            className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
              idx === currentStep
                ? "bg-zinc-800 border-emerald-700"
                : instruction.completed
                ? "bg-zinc-900/50 border-zinc-800"
                : "bg-zinc-900 border-zinc-800 opacity-60"
            }`}
            onClick={() => onStepChange(idx)}
          >
            <div className="mt-0.5">
              {instruction.completed ? (
                <CheckCircle2 className="size-4 text-emerald-400" />
              ) : (
                <Circle className="size-4 text-zinc-600" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className={`text-sm ${instruction.completed ? "text-zinc-500 line-through" : ""}`}>
                {instruction.title}
              </div>
              <div className="text-xs text-zinc-600 truncate">{instruction.details}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
