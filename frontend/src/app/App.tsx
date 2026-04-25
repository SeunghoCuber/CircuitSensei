import { useState } from "react";
import { CameraView } from "./components/camera-view";
import { AgentDrawer } from "./components/agent-drawer";
import { BreadboardView } from "./components/breadboard-view";
import { InstructionsPanel } from "./components/instructions-panel";
import { ControlPanel } from "./components/control-panel";
import { StatusBar } from "./components/status-bar";
import { useAgentSocket } from "./hooks/use-agent-socket";

export default function App() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const {
    connected,
    isLoading,
    messages,
    sendMessage,
    agentState,
    plan,
    components,
    currentStep,
    verifiedSteps,
  } = useAgentSocket();

  return (
    <div className="size-full flex flex-col bg-zinc-950 text-zinc-100">
      <StatusBar agentState={agentState} onToggleDrawer={() => setDrawerOpen(!drawerOpen)} />

      <div className="flex-1 flex gap-4 p-4 overflow-hidden">
        <div className="flex-1 flex flex-col gap-4 min-w-0">
          <div className="flex-1 flex gap-4 min-h-0">
            <BreadboardView connected={connected} components={components} />
            <InstructionsPanel
              plan={plan}
              currentStep={currentStep}
              verifiedSteps={verifiedSteps}
              agentState={agentState}
            />
          </div>

          <ControlPanel onSend={sendMessage} />
        </div>

        <CameraView
          messages={messages}
          isLoading={isLoading}
          onSend={sendMessage}
        />
      </div>

      <AgentDrawer isOpen={drawerOpen} onClose={() => setDrawerOpen(false)} agentState={agentState} />
    </div>
  );
}
