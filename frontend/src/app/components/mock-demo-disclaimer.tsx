import { Cpu, Sparkles, X } from "lucide-react";
import { Button } from "./ui/button";

interface MockDemoDisclaimerProps {
  open: boolean;
  onClose: () => void;
}

export function MockDemoDisclaimer({ open, onClose }: MockDemoDisclaimerProps) {
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="mock-demo-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/80 p-4 backdrop-blur-sm"
    >
      <div className="relative w-full max-w-lg overflow-hidden rounded-lg border border-emerald-400/30 bg-zinc-950 text-zinc-100 shadow-2xl shadow-emerald-950/40">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-300 to-transparent" />
        <button
          type="button"
          aria-label="Close disclaimer"
          onClick={onClose}
          className="absolute right-3 top-3 rounded-md p-1 text-zinc-500 transition-colors hover:bg-zinc-900 hover:text-zinc-100"
        >
          <X className="size-4" />
        </button>

        <div className="p-6">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-lg border border-emerald-400/30 bg-emerald-950/40">
              <Cpu className="size-5 text-emerald-300" />
            </div>
            <div>
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-emerald-300">
                <Sparkles className="size-3.5" />
                Mock Mode
              </div>
              <h1 id="mock-demo-title" className="mt-1 text-2xl font-semibold leading-tight text-white">
                Pre-generated Circuit Sensei example
              </h1>
            </div>
          </div>

          <p className="text-sm leading-6 text-zinc-300">
            This is a pre-generated example of a conversation with Circuit Sensei. The chat,
            instructions, component list, and annotation images will advance through a scripted
            Arduino UNO circuit build.
          </p>
          <p className="mt-3 text-sm leading-6 text-zinc-300">
            Visit our table to get the full live demo with an Arduino UNO.
          </p>

          <div className="mt-6 flex items-center justify-between gap-3 border-t border-zinc-800 pt-4">
            <span className="text-xs text-zinc-500">Scripted demo mode is active</span>
            <Button type="button" onClick={onClose} className="bg-emerald-500 text-zinc-950 hover:bg-emerald-400">
              Start example
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
