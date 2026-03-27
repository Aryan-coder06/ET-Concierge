"use client";

import type { MarketSnapshot } from "@/components/search/types";

type Props = {
  snapshot: MarketSnapshot;
  layout?: "stack" | "grid";
};

function MiniSparkline({ points }: { points: number[] }) {
  if (points.length === 0) {
    return <div className="mt-2 h-8 border border-dashed border-black/30" />;
  }

  const maxPoint = Math.max(...points);
  const minPoint = Math.min(...points);
  const range = maxPoint - minPoint || 1;
  const polylinePoints = points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * 100;
      const y = 26 - ((point - minPoint) / range) * 18;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox="0 0 100 28" className="mt-2 h-8 w-full overflow-visible" fill="none">
      <polyline
        points={polylinePoints}
        className="insight-trace"
        stroke="currentColor"
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function MarketSnapshotPanel({ snapshot, layout = "stack" }: Props) {
  const isGrid = layout === "grid";

  return (
    <div className="space-y-2">
      <div className={isGrid ? "grid gap-2 xl:grid-cols-3" : "space-y-2"}>
        {snapshot.items.map((item) => {
          const positive = item.change >= 0;

          return (
            <a
              key={item.symbol}
              href={item.href}
              target="_blank"
              rel="noreferrer"
              className="block border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] font-black uppercase tracking-[0.18em] text-black/55">
                    {item.label}
                  </p>
                  <p className="mt-1 text-base font-black">
                    {item.price.toLocaleString("en-IN", {
                      maximumFractionDigits: 2,
                    })}
                  </p>
                </div>
                <div className={`text-right ${positive ? "text-[#1040C0]" : "text-[#D02020]"}`}>
                  <p className="text-[11px] font-black uppercase">
                    {positive ? "+" : ""}
                    {item.change.toFixed(2)}
                  </p>
                  <p className="text-[10px] font-black uppercase tracking-wide">
                    {positive ? "+" : ""}
                    {item.changePct.toFixed(2)}%
                  </p>
                </div>
              </div>

              <div className="mt-2 text-[#121212]">
                <MiniSparkline points={item.sparkline} />
              </div>

              <p className="mt-2 text-[10px] font-black uppercase tracking-[0.18em] text-black/55">
                ET route: {item.etRoute}
              </p>
            </a>
          );
        })}
      </div>

      <div className={isGrid ? "grid gap-2 md:grid-cols-2" : "grid gap-2"}>
        {snapshot.etLinks.map((link) => (
          <a
            key={link.href}
            href={link.href}
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-between border border-black bg-white px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em]"
          >
            <span>{link.label}</span>
            <span className="text-black/55">{link.note}</span>
          </a>
        ))}
      </div>

      <p className="text-[10px] font-black uppercase tracking-[0.16em] text-black/55">
        {snapshot.sourceLabel} ·{" "}
        {new Date(snapshot.asOf).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })}
      </p>
    </div>
  );
}
