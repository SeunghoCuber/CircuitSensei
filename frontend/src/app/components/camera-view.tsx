import { Camera } from "lucide-react";
import { Card } from "./ui/card";

export function CameraView() {
  return (
    <Card className="w-80 bg-zinc-900 border-zinc-800 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Camera className="size-4 text-emerald-400" />
        <span className="text-sm">Live Verification</span>
        <div className="size-2 bg-red-500 rounded-full animate-pulse ml-auto" />
      </div>

      <div className="aspect-video bg-zinc-800 rounded-lg overflow-hidden relative">
        <div className="absolute inset-0 flex items-center justify-center text-zinc-600">
          <div className="text-center space-y-2">
            <Camera className="size-10 mx-auto opacity-30" />
            <div className="text-xs">Camera feed</div>
            <div className="text-[10px] opacity-60">USB webcam</div>
          </div>
        </div>
      </div>

      <div className="mt-3 text-xs text-zinc-500 space-y-1">
        <div>• Overhead view of breadboard</div>
        <div>• AI vision verifies placement</div>
        <div>• Real-time component detection</div>
      </div>
    </Card>
  );
}
