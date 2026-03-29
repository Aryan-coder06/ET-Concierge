"use client";

import type { JourneyEvent, PathNode, PathSnapshot } from "@/components/search/types";

type Props = {
  snapshot?: PathSnapshot | null;
  history?: JourneyEvent[];
  mode?: "compact" | "expanded";
  title?: string;
};

const ACCENT_CLASSES: Record<string, string> = {
  red: "bg-[#D02020] text-white",
  blue: "bg-[#1040C0] text-white",
  yellow: "bg-[#F0C020] text-black",
  black: "bg-[#121212] text-white",
};

function trimLabel(value?: string | null, max = 28) {
  if (!value) return "";
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

function cleanRoute(value?: string | null) {
  return value ? value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()) : "Path";
}

function fallbackSnapshotFromHistory(history?: JourneyEvent[]): PathSnapshot | null {
  const last = history?.at(-1);
  if (!last) return null;

  const primaryProduct =
    last.path_snapshot?.primary_display_product ||
    last.recommended_products?.[0] ||
    last.decision?.primary_recommendation?.display_product ||
    last.decision?.primary_recommendation?.product;

  const secondaryProducts =
    last.path_snapshot?.secondary_products ||
    last.recommended_products?.slice(1, 3) ||
    [];

  const nodes: PathNode[] = [
    {
      id: "route",
      label: cleanRoute(last.route),
      detail: "Route",
      accent: "black",
    },
  ];

  if (primaryProduct) {
    nodes.push({
      id: "primary",
      label: trimLabel(primaryProduct),
      detail: "Primary lane",
      accent: "red",
    });
  }

  for (const [index, product] of secondaryProducts.slice(0, 2).entries()) {
    nodes.push({
      id: `secondary-${index}`,
      label: trimLabel(product),
      detail: "Support lane",
      accent: index === 0 ? "blue" : "yellow",
    });
  }

  const nextAction =
    last.path_snapshot?.next_action ||
    last.navigator_summary?.next_move ||
    last.chips?.[0];

  if (nextAction) {
    nodes.push({
      id: "action",
      label: trimLabel(nextAction, 34),
      detail: "Next move",
      accent: "yellow",
    });
  }

  return {
    route: last.route,
    current_lane: last.path_snapshot?.current_lane || last.decision?.current_lane,
    primary_display_product: primaryProduct,
    secondary_products: secondaryProducts,
    next_action: nextAction,
    summary:
      last.path_snapshot?.summary ||
      last.navigator_summary?.summary ||
      "Luna is using the current conversation to frame the next ET move.",
    nodes,
  };
}

function buildTrail(history?: JourneyEvent[]) {
  if (!history?.length) return [];

  return history
    .slice(-5)
    .reverse()
    .map((event, index) => ({
      id: `${event.timestamp || "event"}-${index}`,
      route: cleanRoute(event.route),
      primary:
        event.path_snapshot?.primary_display_product ||
        event.recommended_products?.[0] ||
        event.decision?.primary_recommendation?.display_product ||
        event.decision?.primary_recommendation?.product ||
        "ET Path",
      detail:
        event.path_snapshot?.summary ||
        event.navigator_summary?.summary ||
        event.user_message ||
        "Journey checkpoint",
      time: event.timestamp,
    }));
}

function NodeBadge({ node, active }: { node: PathNode; active?: boolean }) {
  const accentClass = ACCENT_CLASSES[node.accent || "black"] || ACCENT_CLASSES.black;

  return (
    <div className="relative min-w-[130px] flex-1">
      <div className="absolute left-1/2 top-1/2 hidden h-px w-full -translate-y-1/2 border-t-2 border-dashed border-black/35 md:block" />
      <div className="relative z-10 flex h-full flex-col border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]">
        <span className={`mb-3 inline-flex w-fit items-center gap-2 border border-black px-2 py-1 text-[10px] font-black uppercase tracking-[0.16em] ${accentClass}`}>
          <span className={`inline-block h-2.5 w-2.5 rounded-full border border-black ${active ? "journey-node-pulse" : ""}`} />
          {node.detail}
        </span>
        <p className="text-sm font-black uppercase leading-4">{node.label}</p>
      </div>
    </div>
  );
}

export function JourneyPathMap({
  snapshot,
  history,
  mode = "compact",
  title,
}: Props) {
  const resolvedSnapshot = snapshot || fallbackSnapshotFromHistory(history);
  const nodes = resolvedSnapshot?.nodes || [];
  const trail = buildTrail(history);

  if (!resolvedSnapshot && trail.length === 0) {
    return (
      <div className="border-2 border-black bg-white px-4 py-4 shadow-[4px_4px_0px_0px_black]">
        <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#D02020]">
          Live path
        </p>
        <p className="mt-2 text-sm font-medium leading-6 text-black/70">
          Luna will start mapping a visible ET path here once the conversation builds enough context.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {title ? (
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[#D02020]">
            Live Path
          </p>
          <h3 className="mt-1 text-lg font-black uppercase">{title}</h3>
        </div>
      ) : null}

      {resolvedSnapshot?.summary ? (
        <div className="border-2 border-black bg-[#FFF7D4] px-4 py-3 shadow-[4px_4px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.16em] text-black/55">
            Current Path Summary
          </p>
          <p className="mt-2 text-sm font-medium leading-6">{resolvedSnapshot.summary}</p>
        </div>
      ) : null}

      {nodes.length > 0 ? (
        <div className="relative overflow-hidden border-2 border-black bg-[#F8F8F8] p-4 shadow-[4px_4px_0px_0px_black]">
          <div className="journey-link-flow absolute inset-x-6 top-1/2 hidden h-px -translate-y-1/2 border-t-2 border-dashed border-black/30 md:block" />
          <div className="relative z-10 flex flex-col gap-3 md:flex-row">
            {nodes.map((node, index) => (
              <NodeBadge
                key={node.id}
                node={node}
                active={index === nodes.length - 1}
              />
            ))}
          </div>
        </div>
      ) : null}

      {resolvedSnapshot?.signals?.length ? (
        <div className="flex flex-wrap gap-2">
          {resolvedSnapshot.signals.slice(0, 4).map((signal) => (
            <span
              key={signal}
              className="border border-black bg-white px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.14em]"
            >
              {signal.replaceAll("_", " ")}
            </span>
          ))}
        </div>
      ) : null}

      {mode === "expanded" && trail.length > 0 ? (
        <div className="grid gap-3 lg:grid-cols-2">
          {trail.map((item) => (
            <div
              key={item.id}
              className="border-2 border-black bg-white px-4 py-4 shadow-[4px_4px_0px_0px_black]"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] font-black uppercase tracking-[0.16em] text-[#1040C0]">
                    {item.route}
                  </p>
                  <p className="mt-2 text-sm font-black uppercase leading-5">{trimLabel(item.primary, 30)}</p>
                </div>
                {item.time ? (
                  <span className="text-[10px] font-black uppercase tracking-[0.16em] text-black/45">
                    {new Date(item.time).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                ) : null}
              </div>
              <p className="mt-3 text-sm font-medium leading-6 text-black/72">
                {trimLabel(item.detail, 140)}
              </p>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
