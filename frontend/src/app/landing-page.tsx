import { useNavigate } from "react-router";
import { Cpu, Zap, Eye, ArrowRight, Code, CircuitBoard } from "lucide-react";
import { Button } from "./components/ui/button";

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="size-full bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950 flex items-center justify-center overflow-hidden relative">
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAxMCAwIEwgMTAgNjAgTSAwIDEwIEwgNjAgMTAgTSAyMCAwIEwgMjAgNjAgTSAwIDIwIEwgNjAgMjAgTSAzMCAwIEwgMzAgNjAgTSAwIDMwIEwgNjAgMzAgTSA0MCAwIEwgNDAgNjAgTSAwIDQwIEwgNjAgNDAgTSA1MCAwIEwgNTAgNjAgTSAwIDUwIEwgNjAgNTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgzNCwxOTcsMTM0LDAuMDMpIiBzdHJva2Utd2lkdGg9IjEiLz48L3BhdHRlcm4+PC9kZWZzPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjZ3JpZCkiLz48L3N2Zz4=')] opacity-40" />

      <div className="absolute top-20 right-20 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-20 left-20 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />

      <div className="relative z-10 max-w-4xl mx-auto px-8 text-center">
        <div className="flex items-center justify-center gap-4 mb-8">
          <div className="relative">
            <div className="absolute inset-0 bg-emerald-500/20 rounded-2xl blur-xl" />
            <div className="relative bg-gradient-to-br from-emerald-500 to-emerald-600 p-6 rounded-2xl shadow-2xl">
              <Cpu className="size-16 text-white" />
            </div>
          </div>
          <div className="text-left">
            <h1 className="text-6xl text-white mb-2">Circuit Sensei</h1>
            <div className="flex items-center gap-2 text-emerald-400">
              <div className="size-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-sm">AI-Powered Electronics Assistant</span>
            </div>
          </div>
        </div>

        <p className="text-xl text-zinc-300 mb-12 max-w-2xl mx-auto leading-relaxed">
          Your intelligent breadboard companion. Describe what you want to build,
          and let AI guide you step-by-step with live vision verification and automated testing.
        </p>

        <Button
          onClick={() => navigate('/assistant')}
          className="bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-6 text-lg h-auto rounded-xl shadow-2xl hover:shadow-emerald-500/20 transition-all transform hover:scale-105"
        >
          Start Building
          <ArrowRight className="size-6 ml-3" />
        </Button>

        <div className="grid grid-cols-3 gap-6 mt-20 max-w-3xl mx-auto">
          <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-xl p-6 hover:border-emerald-700 transition-all">
            <div className="size-12 bg-emerald-500/20 rounded-lg flex items-center justify-center mb-4 mx-auto">
              <Code className="size-6 text-emerald-400" />
            </div>
            <h3 className="text-white mb-2">Natural Language</h3>
            <p className="text-sm text-zinc-400">
              Describe circuits in plain English powered by Google Gemini
            </p>
          </div>

          <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-xl p-6 hover:border-blue-700 transition-all">
            <div className="size-12 bg-blue-500/20 rounded-lg flex items-center justify-center mb-4 mx-auto">
              <Eye className="size-6 text-blue-400" />
            </div>
            <h3 className="text-white mb-2">Vision Verification</h3>
            <p className="text-sm text-zinc-400">
              AI verifies each component placement with your webcam
            </p>
          </div>

          <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-xl p-6 hover:border-yellow-700 transition-all">
            <div className="size-12 bg-yellow-500/20 rounded-lg flex items-center justify-center mb-4 mx-auto">
              <Zap className="size-6 text-yellow-400" />
            </div>
            <h3 className="text-white mb-2">Arduino Testing</h3>
            <p className="text-sm text-zinc-400">
              Automated electrical tests via Arduino hardware bridge
            </p>
          </div>
        </div>

        <div className="mt-16 flex items-center justify-center gap-8 text-sm text-zinc-500">
          <div className="flex items-center gap-2">
            <CircuitBoard className="size-4" />
            <span>Breadboard Ready</span>
          </div>
          <div className="h-4 w-px bg-zinc-700" />
          <div className="flex items-center gap-2">
            <Cpu className="size-4" />
            <span>Arduino Uno Compatible</span>
          </div>
          <div className="h-4 w-px bg-zinc-700" />
          <div className="flex items-center gap-2">
            <Eye className="size-4" />
            <span>USB Webcam Required</span>
          </div>
        </div>
      </div>
    </div>
  );
}
