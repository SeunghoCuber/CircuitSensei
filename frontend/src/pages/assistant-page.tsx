import { useState, useEffect } from "react";
import { useAgentSession } from "../hooks/use-agent-session";
import { CameraView } from "../components/camera-view";
import { AgentDrawer } from "../components/agent-drawer";
import { BreadboardView } from "../components/breadboard-view";
import { StepGuide } from "../components/step-guide";
import { ControlPanel } from "../components/control-panel";
import { StatusBar } from "../components/status-bar";
import { AlertCircle } from "lucide-react";

type WorkflowPhase = "idle" | "planning" | "building" | "testing" | "complete";

export function AssistantPage() {
  const {
    session,
    response,
    lastAnalysis,
    frameUrl,
    annotatedUrl,
    loading,
    error,
    next,
    startCircuit,
    refreshImages,
  } = useAgentSession();

  const [drawerOpen, setDrawerOpen] = useState(false);

  // Map backend state to workflow phase
  const mapStateToPhase = (state: string | undefined): WorkflowPhase => {
    if (!state) return "idle";
    switch (state) {
      case "IDLE":
        return "idle";
      case "PLAN":
        return "planning";
      case "INSTRUCT":
      case "VERIFY":
        return "building";
      case "TEST":
        return "testing";
      case "COMPLETE":
        return "complete";
      default:
        return "idle";
    }
  };

  const phase = mapStateToPhase(session?.current_state);
  const currentStep = session?.current_step ? session.current_step - 1 : 0; // Convert 1-based to 0-based

  // Determine verification state based on backend state and analysis
  const getVerificationState = () => {
    if (!session) return "waiting";
    if (session.current_state === "VERIFY") return "verifying";
    if (lastAnalysis?.passed) return "verified";
    if (lastAnalysis && !lastAnalysis.passed) return "failed";
    return "waiting";
  };

  const verificationState = getVerificationState();

  // Refresh images periodically when in building/verify phase
  useEffect(() => {
    if (phase === "building" && session?.current_state === "VERIFY") {
      const interval = setInterval(refreshImages, 2000);
      return () => clearInterval(interval);
    }
  }, [phase, session?.current_state, refreshImages]);

  const handleNext = async () => {
    await next();
    refreshImages();
  };

  const handleStartCircuit = async (goal: string) => {
    await startCircuit(goal);
  };

  return (
    <div className="size-full flex flex-col bg-zinc-950 text-zinc-100">
      <StatusBar phase={phase} onToggleDrawer={() => setDrawerOpen(!drawerOpen)} />

      {error && (
        <div className="bg-red-950/50 border-b border-red-900 px-6 py-3 flex items-center gap-3">
          <AlertCircle className="size-5 text-red-400" />
          <span className="text-sm text-red-300">{error}</span>
        </div>
      )}

      <div className="flex-1 flex gap-4 p-4 overflow-hidden">
        <div className="flex-1 flex flex-col gap-4">
          <div className="flex-1 flex gap-4">
            <BreadboardView
              placementPlan={session?.placement_plan || []}
              breadboardGeometry={session?.breadboard_geometry}
              currentStep={currentStep}
              phase={phase}
            />
            <StepGuide
              currentStep={currentStep}
              placementPlan={session?.placement_plan || []}
              verifiedSteps={session?.verified_steps || []}
              phase={phase}
              verificationState={verificationState}
              lastAnalysis={lastAnalysis}
              response={response}
              loading={loading}
              onNext={handleNext}
            />
          </div>

          <ControlPanel
            onStartCircuit={handleStartCircuit}
            phase={phase}
            loading={loading}
          />
        </div>

        <CameraView
          verificationState={verificationState}
          frameUrl={frameUrl}
          annotatedUrl={annotatedUrl}
        />
      </div>

      <AgentDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        phase={phase}
        session={session}
        response={response}
        lastAnalysis={lastAnalysis}
      />
    </div>
  );
}
