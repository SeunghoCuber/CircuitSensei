import { useEffect, useRef, useState } from "react";
import { Camera, CameraOff, Zap } from "lucide-react";
import { Card } from "./ui/card";

interface BreadboardViewProps {
  connected: boolean;
  components: string[];
  currentStep: number;
  planCount: number;
  annotationImageSrc?: string | null;
}

const REFERENCE_IMAGE_SRC = "/api/reference-image";

export function BreadboardView({
  connected,
  components,
  currentStep,
  planCount,
  annotationImageSrc,
}: BreadboardViewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraOn, setCameraOn] = useState(true);
  const [displaySrc, setDisplaySrc] = useState(REFERENCE_IMAGE_SRC);

  // Webcam
  useEffect(() => {
    if (cameraOn) {
      navigator.mediaDevices
        .getUserMedia({ video: true, audio: false })
        .then((stream) => {
          streamRef.current = stream;
          if (videoRef.current) videoRef.current.srcObject = stream;
        })
        .catch((err) => console.warn("Camera unavailable:", err));
    } else {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
    }
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [cameraOn]);

  // Poll the current step's annotation; fall back to the Arduino + breadboard reference.
  useEffect(() => {
    let cancelled = false;
    let currentBlob = "";

    if (annotationImageSrc) {
      setDisplaySrc((prev) => {
        if (prev.startsWith("blob:")) URL.revokeObjectURL(prev);
        return annotationImageSrc;
      });
      return () => {
        cancelled = true;
      };
    }

    const resetToReference = () => {
      if (currentBlob) {
        URL.revokeObjectURL(currentBlob);
        currentBlob = "";
      }
      setDisplaySrc(REFERENCE_IMAGE_SRC);
    };

    resetToReference();
    if (planCount === 0) {
      return () => {
        cancelled = true;
      };
    }

    const poll = async () => {
      try {
        const step = currentStep + 1;
        const res = await fetch(`/api/annotated-image?step=${step}&v=${Date.now()}`);
        if (cancelled) return;
        if (res.ok) {
          const blob = await res.blob();
          if (cancelled) return;
          const url = URL.createObjectURL(blob);
          setDisplaySrc((prev) => {
            if (prev.startsWith("blob:")) URL.revokeObjectURL(prev);
            return url;
          });
          currentBlob = url;
        } else {
          resetToReference();
        }
      } catch {
        if (!cancelled) resetToReference();
      }
    };

    poll();
    const id = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
      if (currentBlob) URL.revokeObjectURL(currentBlob);
    };
  }, [annotationImageSrc, currentStep, planCount]);

  return (
    <Card className="flex-1 bg-zinc-900 border-zinc-800 p-4 flex flex-col gap-3 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Zap className="size-4 text-yellow-400" />
        <h2 className="text-sm">Breadboard Layout</h2>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setCameraOn((v) => !v)}
            title={cameraOn ? "Turn camera off" : "Turn camera on"}
            className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors"
          >
            {cameraOn ? <Camera className="size-4" /> : <CameraOff className="size-4" />}
          </button>
          <div
            className={`size-2 rounded-full animate-pulse ${connected ? "bg-emerald-500" : "bg-red-500"}`}
          />
        </div>
      </div>

      {/* Camera feed + components row */}
      <div className="flex gap-3 shrink-0">
        <div className="w-108 aspect-video bg-zinc-800 rounded-lg overflow-hidden relative shrink-0">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`w-full h-full object-cover ${cameraOn ? "block" : "hidden"}`}
          />
          {!cameraOn && (
            <div className="absolute inset-0 flex items-center justify-center text-zinc-500">
              <div className="text-center space-y-2">
                <CameraOff className="size-8 mx-auto opacity-30" />
                <div className="text-xs">Camera off</div>
              </div>
            </div>
          )}
        </div>

        {/* Components list */}
        <div className="flex-1 min-w-0 bg-zinc-800/50 rounded-lg p-3 flex flex-col gap-1.5 overflow-y-auto">
          <div className="text-xs font-medium text-zinc-400 shrink-0">Components:</div>
          {components.length === 0 ? (
            <div className="text-xs text-zinc-600 italic">No plan yet</div>
          ) : (
            <ul className="space-y-1">
              {components.map((c, i) => (
                <li key={i} className="text-xs text-zinc-300 leading-snug">
                  {c}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Annotated breadboard image */}
      <div className="flex-1 min-h-0 relative">
        <img
          src={displaySrc}
          alt="Breadboard layout"
          className="absolute inset-0 w-full h-full object-contain rounded"
        />
      </div>
    </Card>
  );
}
