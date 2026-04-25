import { useState } from "react";
import { CameraView } from "./components/camera-view";
import { AgentDrawer } from "./components/agent-drawer";
import { BreadboardView } from "./components/breadboard-view";
import { InstructionsPanel } from "./components/instructions-panel";
import { ControlPanel } from "./components/control-panel";
import { StatusBar } from "./components/status-bar";

export default function App() {
  const [agentState, setAgentState] = useState<string>("idle");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [connections, setConnections] = useState<Array<{
    id: string;
    from: string;
    to: string;
    component?: string;
    color?: string;
  }>>([]);

  return (
    <div className="size-full flex flex-col bg-zinc-950 text-zinc-100">
      <StatusBar agentState={agentState} onToggleDrawer={() => setDrawerOpen(!drawerOpen)} />

      <div className="flex-1 flex gap-4 p-4 overflow-hidden">
        <div className="flex-1 flex flex-col gap-4">
          <div className="flex-1 flex gap-4">
            <BreadboardView connections={connections} currentStep={currentStep} />
            <InstructionsPanel
              currentStep={currentStep}
              onStepChange={setCurrentStep}
              agentState={agentState}
            />
          </div>

          <ControlPanel
            onStateChange={setAgentState}
            onConnectionsUpdate={setConnections}
            onStepChange={setCurrentStep}
          />
        </div>

        <CameraView />
      </div>

      <AgentDrawer isOpen={drawerOpen} onClose={() => setDrawerOpen(false)} agentState={agentState} />
    </div>
  );
}