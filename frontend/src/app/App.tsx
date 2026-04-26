import { useEffect, useState } from "react";
import { CameraView } from "./components/camera-view";
import { BreadboardView } from "./components/breadboard-view";
import { InstructionsPanel } from "./components/instructions-panel";
import { ControlPanel } from "./components/control-panel";
import { StatusBar } from "./components/status-bar";
import { MockDemoDisclaimer } from "./components/mock-demo-disclaimer";
import { NetlistModal } from "./components/netlist-modal";
import { useAgentSocket } from "./hooks/use-agent-socket";

export default function App() {
  const [disclaimerOpen, setDisclaimerOpen] = useState(false);
  const [netlistOpen, setNetlistOpen] = useState(false);
  const {
    connected,
    isLoading,
    ttsEnabled,
    mockMode,
    mockDemoComplete,
    messages,
    sendMessage,
    setTtsEnabled,
    agentState,
    plan,
    components,
    currentStep,
    verifiedSteps,
    annotationImageSrc,
  } = useAgentSocket();

  useEffect(() => {
    if (mockMode) {
      setDisclaimerOpen(true);
    }
  }, [mockMode]);

  return (
    <div className="size-full flex flex-col bg-zinc-950 text-zinc-100">
      <StatusBar
        agentState={agentState}
        onShowNetlist={() => setNetlistOpen(true)}
      />

      <div className="flex-1 flex gap-4 p-4 overflow-hidden">
        <div className="flex-1 flex flex-col gap-4 min-w-0">
          <div className="flex-1 flex gap-4 min-h-0">
            <BreadboardView
              connected={connected}
              components={components}
              currentStep={currentStep}
              planCount={plan.length}
              annotationImageSrc={annotationImageSrc}
              mockMode={mockMode}
            />
            <InstructionsPanel
              plan={plan}
              currentStep={currentStep}
              verifiedSteps={verifiedSteps}
              agentState={agentState}
            />
          </div>

          <ControlPanel onSend={sendMessage} disabled={mockDemoComplete} />
        </div>

        <CameraView
          messages={messages}
          isLoading={isLoading}
          ttsEnabled={ttsEnabled}
          mockMode={mockMode}
          inputDisabled={mockDemoComplete}
          onTtsEnabledChange={setTtsEnabled}
          onSend={sendMessage}
        />
      </div>

      <MockDemoDisclaimer open={disclaimerOpen} onClose={() => setDisclaimerOpen(false)} />
      <NetlistModal open={netlistOpen} onClose={() => setNetlistOpen(false)} />
    </div>
  );
}
