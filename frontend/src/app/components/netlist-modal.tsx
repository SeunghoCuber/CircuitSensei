import { useEffect, useState } from "react";
import { FileCode2, X } from "lucide-react";

interface NetlistModalProps {
  open: boolean;
  onClose: () => void;
}

export function NetlistModal({ open, onClose }: NetlistModalProps) {
  const [netlist, setNetlist] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch("/api/netlist")
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        return res.json();
      })
      .then((data) => {
        if (cancelled) return;
        if (data && typeof data.netlist === "string" && (data.has_plan ?? true)) {
          setNetlist(data.netlist);
        } else {
          setNetlist("No circuit plan available yet.");
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="netlist-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl overflow-hidden rounded-lg border border-emerald-400/30 bg-zinc-950 text-zinc-100 shadow-2xl shadow-emerald-950/40"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-300 to-transparent" />
        <button
          type="button"
          aria-label="Close netlist"
          onClick={onClose}
          className="absolute right-3 top-3 rounded-md p-1 text-zinc-500 transition-colors hover:bg-zinc-900 hover:text-zinc-100"
        >
          <X className="size-4" />
        </button>

        <div className="p-6">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-lg border border-emerald-400/30 bg-emerald-950/40">
              <FileCode2 className="size-5 text-emerald-300" />
            </div>
            <div>
              <h1 id="netlist-title" className="text-xl font-semibold leading-tight text-white">
                Generated Netlist
              </h1>
              <p className="text-xs text-zinc-500">Best-effort SPICE-like view of the current plan</p>
            </div>
          </div>

          <pre className="max-h-[60vh] overflow-auto rounded-md border border-zinc-800 bg-zinc-900/80 p-4 text-xs leading-relaxed text-zinc-200 whitespace-pre-wrap break-words">
            {loading ? "Loading…" : error ? `Failed to load netlist: ${error}` : netlist || "No circuit plan available yet."}
          </pre>
        </div>
      </div>
    </div>
  );
}
