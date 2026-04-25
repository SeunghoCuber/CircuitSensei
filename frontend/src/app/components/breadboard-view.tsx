import { useEffect, useRef, useState } from "react";
import { Camera, CameraOff, Zap } from "lucide-react";
import { Card } from "./ui/card";

interface BreadboardViewProps {
  connected: boolean;
  components: string[];
}

export function BreadboardView({ connected, components }: BreadboardViewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraOn, setCameraOn] = useState(true);
  const [displaySrc, setDisplaySrc] = useState("/breadboard-default.jpg");

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

  // Poll annotated image every 2 s using fetch so the single download feeds the <img> directly via blob URL
  useEffect(() => {
    let cancelled = false;
    let prevBlob = "";

    const poll = async () => {
      try {
        const res = await fetch(`/api/annotated-image?v=${Date.now()}`);
        if (cancelled) return;
        if (res.ok) {
          const blob = await res.blob();
          if (cancelled) return;
          const url = URL.createObjectURL(blob);
          setDisplaySrc((prev) => {
            if (prev.startsWith("blob:")) URL.revokeObjectURL(prev);
            return url;
          });
          prevBlob = url;
        } else {
          if (prevBlob) { URL.revokeObjectURL(prevBlob); prevBlob = ""; }
          setDisplaySrc("/breadboard-default.jpg");
        }
      } catch {
        if (!cancelled) setDisplaySrc("/breadboard-default.jpg");
      }
    };

    poll();
    const id = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
      if (prevBlob) URL.revokeObjectURL(prevBlob);
    };
  }, []);

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
