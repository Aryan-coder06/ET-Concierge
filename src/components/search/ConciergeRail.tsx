"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { JourneyPathMap } from "@/components/journey/JourneyPathMap";
import { MarketSnapshotPanel } from "@/components/search/MarketSnapshotPanel";
import type {
  ChatMessage,
  MarketSnapshot,
  ProfileSnapshot,
  SessionDocument,
} from "@/components/search/types";
import { etCompassContent } from "@/content/etCompassContent";
import { getPromptForProduct } from "@/lib/luna-prompts";

const PRODUCT_LINKS: Record<string, string> = {
  "ET Prime": "https://economictimes.indiatimes.com/prime/about-us",
  "ET Markets": "https://economictimes.indiatimes.com/markets",
  "ET Portfolio": "https://etportfolio.economictimes.indiatimes.com/",
  "ET Wealth Edition": "https://epaper.indiatimes.com/wealth_edition.cms",
  "ET Print Edition": "https://epaper.indiatimes.com/default.cms?pub=et",
  ETMasterclass: "https://masterclass.economictimes.indiatimes.com/",
  "ET Events": "https://et-edge.com/",
  "ET Partner Benefits": "https://economictimes.indiatimes.com/et_benefits.cms?from=mdr",
  "ET Edge Events": "https://et-edge.com/",
};

const DEFAULT_PRODUCTS = [
  "ET Prime",
  "ET Markets",
  "ET Portfolio",
  "ETMasterclass",
  "ET Events",
  "ET Partner Benefits",
];

type RailView = "path" | "context" | "products" | "actions";
type PathLens = "map" | "scores" | "checkpoints";
type ContextLens = "summary" | "market" | "reasoning" | "evidence" | "compare" | "verify";

type Props = {
  headerHeight: number;
  latestAssistantMessage: ChatMessage | null;
  marketSnapshot: MarketSnapshot | null;
  marketSnapshotLoading: boolean;
  railWidth: number;
  session: SessionDocument | null;
  visible: boolean;
  onQuickSend: (query: string) => void;
};

type ProductCard = {
  name: string;
  href: string;
  prompt?: string;
  reason?: string;
  score?: number;
};

type SelectorOption = {
  id: string;
  label: string;
  eyebrow?: string;
};

const VIEW_OPTIONS: Array<{ id: RailView; label: string; eyebrow: string }> = [
  { id: "path", label: "Live Path", eyebrow: "Journey" },
  { id: "context", label: "Live Context", eyebrow: "Signals" },
  { id: "products", label: "ET Routes", eyebrow: "Products" },
  { id: "actions", label: "Next Actions", eyebrow: "Flow" },
];

function prettyLabel(value?: string | null) {
  if (!value) return "Building";
  return value.replaceAll("_", " ");
}

function humanizeVisualHint(value?: string | null) {
  if (!value) return "Adaptive mode";
  return value.replaceAll("_", " ");
}

function buildProfileSnapshot(
  latestAssistantMessage: ChatMessage | null,
  session: SessionDocument | null
) {
  const profile: ProfileSnapshot =
    session?.profile || session?.journey_history?.at(-1)?.profile_snapshot || {};
  const currentLane =
    latestAssistantMessage?.pathSnapshot?.primary_display_product ||
    latestAssistantMessage?.decision?.primary_recommendation?.display_product ||
    latestAssistantMessage?.recommendedProducts?.[0] ||
    session?.recommended_products?.[0] ||
    "ET Compass";

  return {
    name: profile.name,
    persona: prettyLabel(profile.profession),
    goal: prettyLabel(profile.goal),
    currentLane,
    onboardingComplete: session?.onboarding_complete ?? false,
  };
}

function buildProductCards(
  latestAssistantMessage: ChatMessage | null,
  session: SessionDocument | null
) {
  const scored = latestAssistantMessage?.decision?.scored_products || [];
  const seen = new Set<string>();
  const cards: ProductCard[] = [];

  const addProduct = (productName?: string | null, reason?: string, score?: number) => {
    if (!productName || seen.has(productName) || !PRODUCT_LINKS[productName]) return;
    seen.add(productName);
    cards.push({
      name: productName,
      href: PRODUCT_LINKS[productName],
      prompt: getPromptForProduct(productName),
      reason,
      score,
    });
  };

  for (const item of scored) {
    const name = item.display_product || item.product;
    addProduct(name, item.reasons?.[0], item.score);
  }

  for (const product of latestAssistantMessage?.recommendedProducts || []) {
    addProduct(product);
  }

  for (const product of session?.recommended_products || []) {
    addProduct(product);
  }

  for (const product of DEFAULT_PRODUCTS) {
    addProduct(product);
  }

  return cards.slice(0, 6);
}

function buildContextSummary(
  latestAssistantMessage: ChatMessage | null,
  session: SessionDocument | null
) {
  const lastJourney = session?.journey_history?.at(-1);
  const summary =
    latestAssistantMessage?.navigatorSummary?.summary ||
    latestAssistantMessage?.pathSnapshot?.summary ||
    lastJourney?.navigator_summary?.summary ||
    lastJourney?.path_snapshot?.summary ||
    "Luna adapts this area to the live ET path, signals, and next move in the conversation.";
  const title =
    latestAssistantMessage?.navigatorSummary?.title ||
    lastJourney?.navigator_summary?.title ||
    latestAssistantMessage?.pathSnapshot?.primary_display_product ||
    "Adaptive ET view";
  const bullets = [
    ...(latestAssistantMessage?.navigatorSummary?.why_this_path || []),
    ...(latestAssistantMessage?.bulletGroups?.flatMap((group) => group.items) || []),
    ...(latestAssistantMessage?.verificationNotes || []),
  ].slice(0, 4);

  return { title, summary, bullets };
}

function buildRecentCheckpoints(session: SessionDocument | null) {
  return (session?.journey_history || [])
    .slice(-4)
    .reverse()
    .map((event, index) => ({
      id: `${event.timestamp || "checkpoint"}-${index}`,
      route: prettyLabel(event.route),
      lane:
        event.path_snapshot?.primary_display_product ||
        event.recommended_products?.[0] ||
        event.decision?.primary_recommendation?.display_product ||
        "ET Path",
      detail:
        event.path_snapshot?.summary ||
        event.navigator_summary?.summary ||
        event.user_message ||
        "Stored journey checkpoint",
    }));
}

function buildActionBuckets(latestAssistantMessage: ChatMessage | null) {
  const roadmapSteps = latestAssistantMessage?.roadmap?.steps?.slice(0, 4) || [];
  const chips = latestAssistantMessage?.chips?.slice(0, 4) || [];
  const nextAction = latestAssistantMessage?.decision?.next_best_action;
  const fallbackPrompt =
    latestAssistantMessage?.pathSnapshot?.next_action ||
    latestAssistantMessage?.navigatorSummary?.next_move ||
    chips[0];

  return {
    roadmapSteps,
    chips,
    nextAction,
    fallbackPrompt,
  };
}

function LensSelector({
  activeId,
  onChange,
  options,
}: {
  activeId: string;
  onChange: (value: string) => void;
  options: SelectorOption[];
}) {
  if (options.length <= 1) return null;

  return (
    <section className="border-2 border-black bg-white p-2 shadow-[3px_3px_0px_0px_black]">
      <div className="flex gap-2 overflow-x-auto pb-1">
        {options.map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => onChange(option.id)}
            className={`shrink-0 border-2 border-black px-3 py-2 text-left shadow-[3px_3px_0px_0px_black] transition-transform hover:-translate-y-0.5 ${
              activeId === option.id ? "bg-[#F0C020]" : "bg-[#F8F8F8]"
            }`}
          >
            {option.eyebrow ? (
              <p className="text-[8px] font-black uppercase tracking-[0.18em] text-black/50">
                {option.eyebrow}
              </p>
            ) : null}
            <p className="mt-1 text-[10px] font-black uppercase tracking-[0.14em]">
              {option.label}
            </p>
          </button>
        ))}
      </div>
    </section>
  );
}

function ViewSelector({
  activeView,
  onChange,
}: {
  activeView: RailView;
  onChange: (value: RailView) => void;
}) {
  return (
    <section className="border-2 border-black bg-[#F8F8F8] p-3 shadow-[4px_4px_0px_0px_black]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020]">
            Control Surface
          </p>
          <h3 className="mt-1 text-sm font-black uppercase">Choose what to inspect</h3>
        </div>
        <select
          value={activeView}
          onChange={(event) => onChange(event.target.value as RailView)}
          className="border-2 border-black bg-white px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] outline-none"
        >
          {VIEW_OPTIONS.map((view) => (
            <option key={view.id} value={view.id}>
              {view.label}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        {VIEW_OPTIONS.map((view) => (
          <button
            key={view.id}
            type="button"
            onClick={() => onChange(view.id)}
            className={`border-2 border-black px-3 py-2 text-left shadow-[3px_3px_0px_0px_black] transition-transform hover:-translate-y-0.5 ${
              activeView === view.id ? "bg-[#F0C020]" : "bg-white"
            }`}
          >
            <p className="text-[9px] font-black uppercase tracking-[0.2em] text-black/55">
              {view.eyebrow}
            </p>
            <p className="mt-1 text-[11px] font-black uppercase">{view.label}</p>
          </button>
        ))}
      </div>
    </section>
  );
}

function ProfileGatewaySection({
  latestAssistantMessage,
  session,
}: {
  latestAssistantMessage: ChatMessage | null;
  session: SessionDocument | null;
}) {
  const profile = buildProfileSnapshot(latestAssistantMessage, session);

  return (
    <section className="border-2 border-black bg-[#FFF7D4] p-3 shadow-[4px_4px_0px_0px_black]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020]">
            Profile Snapshot
          </p>
          <h3 className="mt-1 text-sm font-black uppercase">
            {profile.name ? `${profile.name}'s ET view` : "Current ET view"}
          </h3>
        </div>
        <span className="border border-black bg-white px-2 py-1 text-[9px] font-black uppercase tracking-[0.18em]">
          {profile.onboardingComplete ? "Ready" : "In progress"}
        </span>
      </div>

      <div className="mt-3 grid gap-2">
        <div className="grid grid-cols-2 gap-2">
          <span className="border border-black bg-white px-2.5 py-1.5 text-[10px] font-black uppercase tracking-[0.16em]">
            Persona: {profile.persona}
          </span>
          <span className="border border-black bg-white px-2.5 py-1.5 text-[10px] font-black uppercase tracking-[0.16em]">
            Goal: {profile.goal}
          </span>
        </div>
        <span className="border border-black bg-white px-2.5 py-1.5 text-[10px] font-black uppercase tracking-[0.16em]">
          Current lane: {profile.currentLane}
        </span>
      </div>

      <Link
        href="/profile"
        className="mt-3 flex items-center justify-between border-2 border-black bg-white px-3 py-2.5 text-[10px] font-black uppercase tracking-[0.18em] shadow-[3px_3px_0px_0px_black] transition-transform hover:-translate-y-0.5"
      >
        Open Profile Dashboard
        <span aria-hidden="true">→</span>
      </Link>
    </section>
  );
}

function PathView({
  latestAssistantMessage,
  session,
}: {
  latestAssistantMessage: ChatMessage | null;
  session: SessionDocument | null;
}) {
  const checkpoints = buildRecentCheckpoints(session);
  const scoredProducts = latestAssistantMessage?.decision?.scored_products?.slice(0, 3) || [];
  const nodeCount = latestAssistantMessage?.pathSnapshot?.nodes?.length || 0;
  const routeLabel = prettyLabel(
    latestAssistantMessage?.pathSnapshot?.route || session?.journey_history?.at(-1)?.route
  );
  const currentLane =
    latestAssistantMessage?.pathSnapshot?.primary_display_product ||
    latestAssistantMessage?.decision?.primary_recommendation?.display_product ||
    session?.recommended_products?.[0] ||
    "ET Compass";
  const pathSignalCount = Math.max(
    latestAssistantMessage?.pathSnapshot?.signals?.length || 0,
    latestAssistantMessage?.decision?.signals?.length || 0
  );
  const pathOptions = useMemo<SelectorOption[]>(
    () => [
      { id: "map", label: "Route Map", eyebrow: "Live" },
      ...(scoredProducts.length > 0
        ? [{ id: "scores", label: "Lane Scores", eyebrow: "Scoring" }]
        : []),
      ...(checkpoints.length > 0
        ? [{ id: "checkpoints", label: "Checkpoints", eyebrow: "History" }]
        : []),
    ],
    [checkpoints.length, scoredProducts.length]
  );
  const [selectedLens, setSelectedLens] = useState<PathLens>("map");
  const activeLens = pathOptions.some((option) => option.id === selectedLens)
    ? selectedLens
    : (pathOptions[0]?.id as PathLens);

  return (
    <div className="space-y-3">
      <section className="border-2 border-black bg-[#F8F8F8] p-3 shadow-[4px_4px_0px_0px_black]">
        <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#1040C0]">
          Live route focus
        </p>
        <div className="mt-3 grid grid-cols-3 gap-2">
          <div className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]">
            <p className="text-[9px] font-black uppercase tracking-[0.16em] text-black/55">
              Route
            </p>
            <p className="mt-2 text-[11px] font-black uppercase">{routeLabel}</p>
          </div>
          <div className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]">
            <p className="text-[9px] font-black uppercase tracking-[0.16em] text-black/55">
              Active lane
            </p>
            <p className="mt-2 text-[11px] font-black uppercase">{currentLane}</p>
          </div>
          <div className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]">
            <p className="text-[9px] font-black uppercase tracking-[0.16em] text-black/55">
              Signals
            </p>
            <p className="mt-2 text-[11px] font-black uppercase">
              {Math.max(nodeCount, pathSignalCount)}
            </p>
          </div>
        </div>
      </section>

      <LensSelector
        activeId={activeLens}
        onChange={(value) => setSelectedLens(value as PathLens)}
        options={pathOptions}
      />

      {activeLens === "map" ? (
        <JourneyPathMap
          snapshot={latestAssistantMessage?.pathSnapshot}
          history={session?.journey_history}
          title="How Luna is shaping the current ET route"
        />
      ) : null}

      {activeLens === "scores" && scoredProducts.length > 0 ? (
        <section className="border-2 border-black bg-[#F8F8F8] p-3 shadow-[4px_4px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#1040C0]">
            Lane scoring
          </p>
          <div className="mt-3 space-y-2">
            {scoredProducts.map((item) => {
              const name = item.display_product || item.product || "ET Lane";
              const score = Math.max(0, Math.min(100, Math.round(item.score || 0)));

              return (
                <div
                  key={name}
                  className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[11px] font-black uppercase">{name}</p>
                    <span className="text-[10px] font-black uppercase tracking-[0.16em] text-black/55">
                      {score}
                    </span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden border border-black bg-[#F0F0F0]">
                    <div
                      className="h-full bg-[#1040C0]"
                      style={{ width: `${score}%` }}
                    />
                  </div>
                  {item.reasons?.[0] ? (
                    <p className="mt-2 text-[11px] font-medium leading-5 text-black/72">
                      {item.reasons[0]}
                    </p>
                  ) : null}
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {activeLens === "checkpoints" && checkpoints.length > 0 ? (
        <section className="border-2 border-black bg-[#DDE7FF] p-3 shadow-[4px_4px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#1040C0]">
            Recent checkpoints
          </p>
          <div className="mt-3 space-y-2">
            {checkpoints.map((item) => (
              <div
                key={item.id}
                className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]"
              >
                <p className="text-[10px] font-black uppercase tracking-[0.16em] text-[#D02020]">
                  {item.route}
                </p>
                <p className="mt-1 text-[11px] font-black uppercase">{item.lane}</p>
                <p className="mt-2 text-[11px] font-medium leading-5 text-black/72">
                  {item.detail}
                </p>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function ContextView({
  latestAssistantMessage,
  marketSnapshot,
  marketSnapshotLoading,
  session,
}: {
  latestAssistantMessage: ChatMessage | null;
  marketSnapshot: MarketSnapshot | null;
  marketSnapshotLoading: boolean;
  session: SessionDocument | null;
}) {
  const summary = buildContextSummary(latestAssistantMessage, session);
  const decision = latestAssistantMessage?.decision;
  const uiModules = (latestAssistantMessage?.uiModules || []).filter(
    (module) => module.visible !== false
  );
  const showMarketSnapshot =
    !!marketSnapshot &&
    ["markets_tools", "portfolio_view"].includes(latestAssistantMessage?.visualHint || "");
  const comparisonRows = latestAssistantMessage?.comparisonRows?.slice(0, 4) || [];
  const verificationNotes = latestAssistantMessage?.verificationNotes?.slice(0, 4) || [];
  const sourceCitations = latestAssistantMessage?.sourceCitations?.slice(0, 5) || [];
  const reasoningCards = [
    {
      label: "Primary lane",
      value:
        latestAssistantMessage?.pathSnapshot?.primary_display_product ||
        decision?.primary_recommendation?.display_product ||
        session?.recommended_products?.[0] ||
        "ET Compass",
      note:
        decision?.primary_recommendation?.why?.[0] ||
        summary.bullets[0] ||
        "Current front-running ET path from the live answer.",
      accent: "bg-[#D02020]",
    },
    {
      label: "Response mode",
      value:
        latestAssistantMessage?.answerStyle ||
        humanizeVisualHint(latestAssistantMessage?.visualHint),
      note: "Current answer format Luna is using for this thread.",
      accent: "bg-[#1040C0]",
    },
    {
      label: "Active modules",
      value: `${uiModules.length || 1}`,
      note: "Live UI blocks selected from the current answer state.",
      accent: "bg-[#F0C020]",
    },
  ];
  const contextOptions = useMemo<SelectorOption[]>(
    () => [
      { id: "summary", label: "Summary", eyebrow: "Live" },
      ...(showMarketSnapshot || marketSnapshotLoading
        ? [{ id: "market", label: "Market", eyebrow: "Snapshot" }]
        : []),
      { id: "reasoning", label: "Reasoning", eyebrow: "Route" },
      ...(sourceCitations.length > 0
        ? [{ id: "evidence", label: "Evidence", eyebrow: "Sources" }]
        : []),
      ...(comparisonRows.length > 0
        ? [{ id: "compare", label: "Compare", eyebrow: "Structured" }]
        : []),
      ...(verificationNotes.length > 0
        ? [{ id: "verify", label: "Verify", eyebrow: "Trust" }]
        : []),
    ],
    [
      comparisonRows.length,
      marketSnapshotLoading,
      showMarketSnapshot,
      sourceCitations.length,
      verificationNotes.length,
    ]
  );
  const [selectedLens, setSelectedLens] = useState<ContextLens>(
    showMarketSnapshot ? "market" : comparisonRows.length > 0 ? "compare" : "summary"
  );
  const preferredLens: ContextLens =
    showMarketSnapshot || marketSnapshotLoading
      ? "market"
      : comparisonRows.length > 0
        ? "compare"
        : verificationNotes.length > 0
          ? "verify"
          : "summary";

  const activeLens = contextOptions.some((option) => option.id === selectedLens)
    ? selectedLens
    : preferredLens;

  return (
    <div className="space-y-3">
      <section className="border-2 border-black bg-[#FFE6E6] p-3 shadow-[4px_4px_0px_0px_black]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020]">
              Live context
            </p>
            <h3 className="mt-1 text-sm font-black uppercase">{summary.title}</h3>
          </div>
          <span className="border border-black bg-white px-2 py-1 text-[9px] font-black uppercase tracking-[0.18em]">
            {humanizeVisualHint(latestAssistantMessage?.visualHint)}
          </span>
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2">
          <div className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]">
            <p className="text-[9px] font-black uppercase tracking-[0.16em] text-black/55">
              Primary lane
            </p>
            <p className="mt-2 text-[11px] font-black uppercase">
              {reasoningCards[0].value}
            </p>
          </div>
          <div className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]">
            <p className="text-[9px] font-black uppercase tracking-[0.16em] text-black/55">
              Sources
            </p>
            <p className="mt-2 text-[11px] font-black uppercase">{sourceCitations.length}</p>
          </div>
          <div className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]">
            <p className="text-[9px] font-black uppercase tracking-[0.16em] text-black/55">
              Modules
            </p>
            <p className="mt-2 text-[11px] font-black uppercase">{uiModules.length || 1}</p>
          </div>
        </div>
      </section>

      <LensSelector
        activeId={activeLens}
        onChange={(value) => setSelectedLens(value as ContextLens)}
        options={contextOptions}
      />

      {activeLens === "market" && (showMarketSnapshot || marketSnapshotLoading) ? (
        <section className="border-2 border-black bg-[#FFE6E6] p-3 shadow-[4px_4px_0px_0px_black]">
          {showMarketSnapshot ? (
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020]">
                Structured market snapshot
              </p>
              <div className="mt-3">
                <MarketSnapshotPanel snapshot={marketSnapshot} />
              </div>
            </div>
          ) : (
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#D02020]">
                Pulling live market context
              </p>
              <div className="mt-3 flex items-end gap-2">
                {[1, 2, 3, 4].map((bar) => (
                  <span
                    key={bar}
                    className="signal-bar w-6 border-2 border-black bg-[#D02020]"
                    style={{ height: `${24 + bar * 10}px`, animationDelay: `${bar * 0.1}s` }}
                  />
                ))}
              </div>
            </div>
          )}
        </section>
      ) : null}

      {activeLens === "summary" ? (
        <section className="border-2 border-black bg-white p-3 shadow-[4px_4px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#1040C0]">
            Current thread summary
          </p>
          <p className="mt-3 text-[12px] font-medium leading-6 text-black/78">
            {summary.summary}
          </p>
          {summary.bullets.length > 0 ? (
            <div className="mt-3 space-y-2">
              {summary.bullets.map((item) => (
                <div
                  key={item}
                  className="border border-black bg-[#F8F8F8] px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em]"
                >
                  {item}
                </div>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      {activeLens === "reasoning" ? (
        <section className="grid gap-2">
          {reasoningCards.map((card) => (
            <div
              key={card.label}
              className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]"
            >
              <span className={`block h-1.5 w-16 ${card.accent}`} />
              <p className="mt-3 text-[10px] font-black uppercase tracking-[0.16em] text-black/55">
                {card.label}
              </p>
              <p className="mt-1 text-[12px] font-black uppercase">{card.value}</p>
              <p className="mt-2 text-[11px] font-medium leading-5 text-black/72">
                {card.note}
              </p>
            </div>
          ))}
          {decision?.signals?.length ? (
            <div className="border-2 border-black bg-[#F8F8F8] px-3 py-3 shadow-[3px_3px_0px_0px_black]">
              <p className="text-[10px] font-black uppercase tracking-[0.16em] text-[#1040C0]">
                Signals Luna is reading
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {decision.signals.slice(0, 6).map((signal) => (
                  <span
                    key={signal}
                    className="border border-black bg-white px-2.5 py-1.5 text-[10px] font-black uppercase tracking-[0.14em]"
                  >
                    {prettyLabel(signal)}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

      {activeLens === "evidence" && sourceCitations.length > 0 ? (
        <section className="border-2 border-black bg-white p-3 shadow-[4px_4px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#1040C0]">
            Source evidence
          </p>
          <div className="mt-3 space-y-2">
            {sourceCitations.map((citation, index) => (
              <div
                key={`${citation.label}-${citation.href || index}`}
                className="border-2 border-black bg-[#F8F8F8] px-3 py-3 shadow-[3px_3px_0px_0px_black]"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-[11px] font-black uppercase">{citation.label}</p>
                  <span className="border border-black bg-white px-2 py-1 text-[9px] font-black uppercase tracking-[0.14em]">
                    {citation.pageType || "source"}
                  </span>
                </div>
                <p className="mt-2 text-[10px] font-black uppercase tracking-[0.14em] text-black/55">
                  {citation.verificationStatus || "grounded"}
                </p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {activeLens === "compare" && comparisonRows.length > 0 ? (
        <section className="border-2 border-black bg-[#DDE7FF] p-3 shadow-[4px_4px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#1040C0]">
            Structured comparison
          </p>
          <div className="mt-3 space-y-2">
            {comparisonRows.map((row) => (
              <div
                key={`${row.item}-${row.best_for}`}
                className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]"
              >
                <p className="text-[11px] font-black uppercase">{row.item}</p>
                <p className="mt-2 text-[10px] font-black uppercase tracking-[0.16em] text-[#1040C0]">
                  Best for {row.best_for}
                </p>
                <p className="mt-2 text-[11px] font-medium leading-5 text-black/74">{row.why}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {activeLens === "verify" && verificationNotes.length > 0 ? (
        <section className="border-2 border-black bg-[#FFF7D4] p-3 shadow-[4px_4px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020]">
            Verification notes
          </p>
          <div className="mt-3 space-y-2">
            {verificationNotes.map((note) => (
              <div
                key={note}
                className="border-2 border-black bg-white px-3 py-3 text-[11px] font-medium leading-5 shadow-[3px_3px_0px_0px_black]"
              >
                {note}
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function ProductsView({
  latestAssistantMessage,
  onQuickSend,
  session,
}: {
  latestAssistantMessage: ChatMessage | null;
  onQuickSend: (query: string) => void;
  session: SessionDocument | null;
}) {
  const products = buildProductCards(latestAssistantMessage, session);

  return (
    <div className="space-y-3">
      <section className="border-2 border-black bg-[#DDE7FF] p-3 shadow-[4px_4px_0px_0px_black]">
        <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#1040C0]">
          ET routes
        </p>
        <h3 className="mt-1 text-sm font-black uppercase">
          Switch between the strongest ET surfaces
        </h3>
        <p className="mt-2 text-[12px] font-medium leading-6 text-black/75">
          These cards now follow the live answer instead of staying locked to one static lane.
        </p>
      </section>

      <div className="space-y-2">
        {products.map((product) => (
          <div
            key={product.name}
            className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] font-black uppercase">{product.name}</p>
                {typeof product.score === "number" ? (
                  <p className="mt-1 text-[10px] font-black uppercase tracking-[0.16em] text-black/55">
                    Match score {Math.round(product.score)}
                  </p>
                ) : null}
              </div>
              <span className="border border-black bg-[#F8F8F8] px-2 py-1 text-[9px] font-black uppercase tracking-[0.16em]">
                ET
              </span>
            </div>

            <p className="mt-2 text-[11px] font-medium leading-5 text-black/72">
              {product.reason || "Ask Luna to explain where this product fits in your journey."}
            </p>

            <div className="mt-3 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => onQuickSend(product.prompt || `Show me how ${product.name} fits my ET journey.`)}
                className="border-2 border-black bg-[#F0C020] px-3 py-2 text-[10px] font-black uppercase tracking-[0.14em] shadow-[3px_3px_0px_0px_black] transition-transform hover:-translate-y-0.5"
              >
                Ask Luna
              </button>
              <a
                href={product.href}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center border-2 border-black bg-white px-3 py-2 text-[10px] font-black uppercase tracking-[0.14em] shadow-[3px_3px_0px_0px_black] transition-transform hover:-translate-y-0.5"
              >
                Open ET
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ActionsView({
  latestAssistantMessage,
  onQuickSend,
}: {
  latestAssistantMessage: ChatMessage | null;
  onQuickSend: (query: string) => void;
}) {
  const actions = buildActionBuckets(latestAssistantMessage);

  return (
    <div className="space-y-3">
      {actions.roadmapSteps.length > 0 ? (
        <section className="border-2 border-black bg-[#E7F7EA] p-3 shadow-[4px_4px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#163A21]">
            Guided roadmap
          </p>
          <div className="mt-3 space-y-2">
            {actions.roadmapSteps.map((step) => (
              <button
                key={`${step.step}-${step.product}`}
                type="button"
                onClick={() => onQuickSend(`Help me explore ${step.product} and explain why it matters now.`)}
                className="flex w-full items-start gap-2 border-2 border-black bg-white px-3 py-2.5 text-left shadow-[3px_3px_0px_0px_black]"
              >
                <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center border-2 border-black bg-[#F0C020] text-[10px] font-black">
                  {step.step}
                </span>
                <span className="min-w-0">
                  <span className="block text-[10px] font-black uppercase">{step.product}</span>
                  <span className="mt-1 block text-[10px] font-medium leading-4 text-black/75">
                    {step.reason}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {actions.nextAction ? (
        <section className="border-2 border-black bg-[#FFF7D4] p-3 shadow-[4px_4px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020]">
            Next best action
          </p>
          <div className="mt-3 border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]">
            <p className="text-[10px] font-black uppercase">{actions.nextAction.label || "Continue with Luna"}</p>
            {actions.nextAction.reason ? (
              <p className="mt-2 text-[11px] font-medium leading-5 text-black/72">
                {actions.nextAction.reason}
              </p>
            ) : null}
            <button
              type="button"
              onClick={() =>
                onQuickSend(
                  actions.nextAction?.reason ||
                    actions.nextAction?.label ||
                    "Guide me to the best ET next move."
                )
              }
              className="mt-3 border-2 border-black bg-[#F0C020] px-3 py-2 text-[10px] font-black uppercase tracking-[0.14em] shadow-[3px_3px_0px_0px_black]"
            >
              Use this path
            </button>
          </div>
        </section>
      ) : null}

      {actions.chips.length > 0 ? (
        <section className="border-2 border-black bg-white p-3 shadow-[4px_4px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#1040C0]">
            Prompt boosters
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {actions.chips.map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => onQuickSend(chip)}
                className="border border-black bg-[#F8F8F8] px-2.5 py-1.5 text-[10px] font-black uppercase tracking-[0.14em]"
              >
                {chip}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {!actions.roadmapSteps.length && !actions.nextAction && actions.fallbackPrompt ? (
        <section className="border-2 border-black bg-white p-3 shadow-[4px_4px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#1040C0]">
            Best next prompt
          </p>
          <button
            type="button"
            onClick={() => onQuickSend(actions.fallbackPrompt!)}
            className="mt-3 w-full border-2 border-black bg-[#F0C020] px-3 py-3 text-left text-[10px] font-black uppercase tracking-[0.16em] shadow-[3px_3px_0px_0px_black]"
          >
            {actions.fallbackPrompt}
          </button>
        </section>
      ) : null}
    </div>
  );
}

export function ConciergeRail({
  headerHeight,
  latestAssistantMessage,
  marketSnapshot,
  marketSnapshotLoading,
  railWidth,
  session,
  visible,
  onQuickSend,
}: Props) {
  const [activeView, setActiveView] = useState<RailView>("path");

  const headerProduct = useMemo(
    () =>
      latestAssistantMessage?.pathSnapshot?.primary_display_product ||
      latestAssistantMessage?.decision?.primary_recommendation?.display_product ||
      session?.recommended_products?.[0] ||
      "ET Compass",
    [latestAssistantMessage, session]
  );

  if (!visible) return null;

  return (
    <aside
      className="fixed right-0 z-30 hidden border-l-4 border-black bg-white xl:block"
      style={{
        top: `${headerHeight}px`,
        height: `calc(100vh - ${headerHeight}px)`,
        width: `${railWidth}px`,
      }}
    >
      <div className="flex h-full flex-col overflow-hidden">
        <div className="border-b-4 border-black p-4">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020]">
            Concierge Rail
          </p>
          <h2 className="mt-1 font-black uppercase text-lg">Luna Control Center</h2>
          <p className="mt-2 text-[11px] font-medium leading-5 text-black/68">
            Live route focus: <span className="font-black uppercase text-black">{headerProduct}</span>
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <div className="space-y-3">
            <ProfileGatewaySection
              latestAssistantMessage={latestAssistantMessage}
              session={session}
            />

            <ViewSelector activeView={activeView} onChange={setActiveView} />

            {activeView === "path" ? (
              <PathView
                latestAssistantMessage={latestAssistantMessage}
                session={session}
              />
            ) : null}

            {activeView === "context" ? (
              <ContextView
                latestAssistantMessage={latestAssistantMessage}
                marketSnapshot={marketSnapshot}
                marketSnapshotLoading={marketSnapshotLoading}
                session={session}
              />
            ) : null}

            {activeView === "products" ? (
              <ProductsView
                latestAssistantMessage={latestAssistantMessage}
                session={session}
                onQuickSend={onQuickSend}
              />
            ) : null}

            {activeView === "actions" ? (
              <ActionsView
                latestAssistantMessage={latestAssistantMessage}
                onQuickSend={onQuickSend}
              />
            ) : null}
          </div>
        </div>

        <div className="border-t-4 border-black p-3">
          <Link
            href="/"
            className="flex w-full items-center justify-center border-2 border-black bg-[#F0C020] px-3 py-2.5 text-xs font-black uppercase tracking-wide shadow-[4px_4px_0px_0px_black]"
          >
            {etCompassContent.searchPage.secondaryButton}
          </Link>
        </div>
      </div>
    </aside>
  );
}
