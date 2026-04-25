import { Zap } from "lucide-react";
import { Card } from "./ui/card";

interface Connection {
  id: string;
  from: string;
  to: string;
  component?: string;
  color?: string;
}

interface BreadboardViewProps {
  connections: Connection[];
  currentStep: number;
}

export function BreadboardView({ connections, currentStep }: BreadboardViewProps) {
  const rows = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"];
  const cols = Array.from({ length: 30 }, (_, i) => i + 1);

  const getHoleColor = (row: string, col: number) => {
    const connection = connections.find(
      (c) => c.from === `${row}${col}` || c.to === `${row}${col}`
    );
    return connection?.color || "transparent";
  };

  return (
    <Card className="flex-1 bg-zinc-900 border-zinc-800 p-6 overflow-auto">
      <div className="flex items-center gap-2 mb-6">
        <Zap className="size-5 text-yellow-400" />
        <h2>Breadboard Layout</h2>
      </div>

      <div className="inline-block min-w-max">
        <div className="bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg p-6 shadow-2xl border-4 border-zinc-700">
          {/* Power rails top */}
          <div className="flex gap-2 mb-4">
            <div className="flex items-center gap-1">
              <div className="w-8 h-3 bg-red-600 rounded-sm border border-red-800 text-[8px] text-white flex items-center justify-center">+</div>
              {cols.map((col) => (
                <div key={`power-top-${col}`} className="w-3 h-3 bg-red-400 rounded-full border border-red-600" />
              ))}
            </div>
          </div>
          <div className="flex gap-2 mb-6">
            <div className="flex items-center gap-1">
              <div className="w-8 h-3 bg-blue-900 rounded-sm border border-blue-950 text-[8px] text-white flex items-center justify-center">-</div>
              {cols.map((col) => (
                <div key={`ground-top-${col}`} className="w-3 h-3 bg-blue-800 rounded-full border border-blue-950" />
              ))}
            </div>
          </div>

          {/* Main breadboard area */}
          <div className="space-y-1">
            {rows.slice(0, 5).map((row) => (
              <div key={row} className="flex items-center gap-1">
                <div className="w-8 text-[10px] text-zinc-600 text-right pr-1">{row}</div>
                {cols.map((col) => {
                  const holeId = `${row}${col}`;
                  const holeColor = getHoleColor(row, col);
                  const isActive = holeColor !== "transparent";

                  return (
                    <div
                      key={holeId}
                      className={`w-3 h-3 rounded-full border transition-all ${
                        isActive
                          ? "border-zinc-700 ring-2 ring-offset-1 scale-125"
                          : "border-zinc-400 bg-zinc-800"
                      }`}
                      style={{
                        backgroundColor: isActive ? holeColor : undefined,
                        ringColor: isActive ? holeColor : undefined,
                      }}
                      title={holeId}
                    />
                  );
                })}
              </div>
            ))}

            {/* Center gap */}
            <div className="h-4 bg-gradient-to-b from-amber-200 to-amber-300 rounded my-1" />

            {rows.slice(5).map((row) => (
              <div key={row} className="flex items-center gap-1">
                <div className="w-8 text-[10px] text-zinc-600 text-right pr-1">{row}</div>
                {cols.map((col) => {
                  const holeId = `${row}${col}`;
                  const holeColor = getHoleColor(row, col);
                  const isActive = holeColor !== "transparent";

                  return (
                    <div
                      key={holeId}
                      className={`w-3 h-3 rounded-full border transition-all ${
                        isActive
                          ? "border-zinc-700 ring-2 ring-offset-1 scale-125"
                          : "border-zinc-400 bg-zinc-800"
                      }`}
                      style={{
                        backgroundColor: isActive ? holeColor : undefined,
                        ringColor: isActive ? holeColor : undefined,
                      }}
                      title={holeId}
                    />
                  );
                })}
              </div>
            ))}
          </div>

          {/* Power rails bottom */}
          <div className="flex gap-2 mt-6">
            <div className="flex items-center gap-1">
              <div className="w-8 h-3 bg-red-600 rounded-sm border border-red-800 text-[8px] text-white flex items-center justify-center">+</div>
              {cols.map((col) => (
                <div key={`power-bottom-${col}`} className="w-3 h-3 bg-red-400 rounded-full border border-red-600" />
              ))}
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <div className="flex items-center gap-1">
              <div className="w-8 h-3 bg-blue-900 rounded-sm border border-blue-950 text-[8px] text-white flex items-center justify-center">-</div>
              {cols.map((col) => (
                <div key={`ground-bottom-${col}`} className="w-3 h-3 bg-blue-800 rounded-full border border-blue-950" />
              ))}
            </div>
          </div>

          {/* Column numbers */}
          <div className="flex gap-1 mt-3 ml-9">
            {cols.map((col) => (
              <div key={`col-${col}`} className="w-3 text-[8px] text-zinc-600 text-center">
                {col % 5 === 0 ? col : ""}
              </div>
            ))}
          </div>
        </div>

        {/* Legend */}
        <div className="mt-4 flex gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500 border border-emerald-700" />
            <span className="text-zinc-400">Component</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500 border border-blue-700" />
            <span className="text-zinc-400">Wire</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-purple-500 border border-purple-700" />
            <span className="text-zinc-400">Power</span>
          </div>
        </div>
      </div>
    </Card>
  );
}
