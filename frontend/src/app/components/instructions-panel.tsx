import { CheckCircle2, Circle, ClipboardList } from "lucide-react";
import { Card } from "./ui/card";
import type { PlanStep } from "../hooks/use-agent-socket";

interface InstructionsPanelProps {
  plan: PlanStep[];
  currentStep: number;   // 0-based index into plan
  verifiedSteps: number[]; // 1-based step numbers that passed verification
  agentState: string;
}

export function InstructionsPanel({ plan, currentStep, verifiedSteps, agentState }: InstructionsPanelProps) {
  const isVerified = (step: PlanStep) => verifiedSteps.includes(step.step);
  const isCurrent = (idx: number) => idx === currentStep;
  const activeStep = plan[currentStep];

  return (
    <Card className="w-96 bg-zinc-900 border-zinc-800 p-4 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ClipboardList className="size-4 text-emerald-400" />
          <h2>Assembly Instructions</h2>
        </div>
        {plan.length > 0 && (
          <span className="text-xs text-zinc-500">
            {verifiedSteps.length} / {plan.length} done
          </span>
        )}
      </div>

      {plan.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-zinc-600">
          <div className="text-center space-y-2">
            <ClipboardList className="size-10 mx-auto opacity-30" />
            <div className="text-sm">No plan yet</div>
            <div className="text-xs opacity-60">Tell the agent your goal to generate steps</div>
          </div>
        </div>
      ) : (
        <>
          {/* Active step highlight */}
          {activeStep && !isVerified(activeStep) && (
            <div className="mb-4 p-4 bg-emerald-950/30 border border-emerald-900/60 rounded-lg">
              <div className="flex items-start gap-3">
                <div className="size-7 shrink-0 rounded-full bg-emerald-500 flex items-center justify-center text-zinc-900 text-sm font-semibold mt-0.5">
                  {activeStep.step}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-zinc-100 leading-relaxed">{activeStep.instruction}</p>
                  {activeStep.verification && (
                    <p className="text-xs text-zinc-500 mt-2">
                      Verify: {activeStep.verification}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {verifiedSteps.length === plan.length && plan.length > 0 && (
            <div className="mb-4 p-3 bg-emerald-900/20 border border-emerald-800/40 rounded-lg text-sm text-emerald-300 text-center">
              All steps complete — ready for testing.
            </div>
          )}

          {/* Step list */}
          <div className="flex-1 overflow-y-auto space-y-1.5">
            {plan.map((step, idx) => {
              const verified = isVerified(step);
              const active = isCurrent(idx) && !verified;
              return (
                <div
                  key={step.step}
                  className={`flex items-start gap-3 p-3 rounded-lg border transition-all ${
                    active
                      ? "bg-zinc-800 border-emerald-800"
                      : verified
                      ? "bg-zinc-900/40 border-zinc-800/60 opacity-60"
                      : "bg-zinc-900 border-zinc-800/40 opacity-50"
                  }`}
                >
                  <div className="mt-0.5 shrink-0">
                    {verified ? (
                      <CheckCircle2 className="size-4 text-emerald-400" />
                    ) : (
                      <Circle className={`size-4 ${active ? "text-emerald-600" : "text-zinc-700"}`} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={`text-xs font-medium mb-0.5 ${active ? "text-emerald-400" : verified ? "text-zinc-600" : "text-zinc-500"}`}>
                      Step {step.step}
                    </div>
                    <div className={`text-sm leading-snug ${verified ? "text-zinc-600 line-through" : active ? "text-zinc-200" : "text-zinc-500"}`}>
                      {step.title ?? step.instruction}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </Card>
  );
}
