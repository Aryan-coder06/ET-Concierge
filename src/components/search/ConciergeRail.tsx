"use client";

import Link from "next/link";
import { MarketSnapshotPanel } from "@/components/search/MarketSnapshotPanel";
import type {
  ChatMessage,
  MarketSnapshot,
  ProfileSnapshot,
  SessionDocument,
} from "@/components/search/types";
import { etCompassContent } from "@/content/etCompassContent";

const PRODUCT_LINKS: Record<string, string> = {
  "ET Prime": "https://economictimes.indiatimes.com/prime/about-us",
  "ET Markets": "https://economictimes.indiatimes.com/markets",
  "ET Portfolio": "https://etportfolio.economictimes.indiatimes.com/",
  "ET Wealth Edition": "https://epaper.indiatimes.com/wealth_edition.cms",
  "ET Print Edition": "https://epaper.indiatimes.com/default.cms?pub=et",
  ETMasterclass: "https://masterclass.economictimes.indiatimes.com/",
  "ET Events": "https://et-edge.com/",
  "ET Partner Benefits": "https://economictimes.indiatimes.com/et_benefits.cms?from=mdr",
};

const DEFAULT_PRODUCTS = [
  "ET Prime",
  "ET Markets",
  "ET Portfolio",
  "ETMasterclass",
  "ET Events",
  "ET Partner Benefits",
];

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
  
function prettyLabel(value?: string | null) {
  if (!value) return "Building";
  return value.replaceAll("_", " ");
}

function buildUseNowProducts(
  recommendedProducts: string[],
  session: SessionDocument | null
) {
  const seen = new Set<string>();
  const ordered = [
    ...recommendedProducts,
    ...(session?.recommended_products || []),
    ...DEFAULT_PRODUCTS,
  ];

  return ordered
    .filter((product) => {
      if (!PRODUCT_LINKS[product] || seen.has(product)) return false;
      seen.add(product);
      return true;
    })
    .slice(0, 6);
}

function buildLiveContextSummary(
  latestAssistantMessage: ChatMessage | null,
  session: SessionDocument | null
) {
  if (latestAssistantMessage?.navigatorSummary) {
    return {
      title: latestAssistantMessage.navigatorSummary.title,
      summary: latestAssistantMessage.navigatorSummary.summary,
      bullets: latestAssistantMessage.navigatorSummary.why_this_path || [],
    };
  }

  const lastJourney = session?.journey_history?.at(-1);
  if (lastJourney?.navigator_summary) {
    return {
      title: lastJourney.navigator_summary.title,
      summary: lastJourney.navigator_summary.summary,
      bullets: lastJourney.navigator_summary.why_this_path || [],
    };
  }

  return {
    title: "ET path in focus",
    summary:
      "Luna will surface the most relevant ET lane here after your next question.",
    bullets: [],
  };
}

function buildNextActions(latestAssistantMessage: ChatMessage | null) {
  const chips = latestAssistantMessage?.chips || [];
  const roadmapSteps = latestAssistantMessage?.roadmap?.steps || [];

  return {
    chips: chips.slice(0, 3),
    roadmapSteps: roadmapSteps.slice(0, 3),
  };
}

function buildProfileSnapshot(
  latestAssistantMessage: ChatMessage | null,
  session: SessionDocument | null
) {
  const profile: ProfileSnapshot =
    session?.profile || session?.journey_history?.at(-1)?.profile_snapshot || {};
  const currentLane =
    latestAssistantMessage?.recommendedProducts?.[0] ||
    session?.recommended_products?.[0] ||
    "ET Compass";

  return {
    persona: prettyLabel(profile.profession),
    goal: prettyLabel(profile.goal),
    currentLane,
    onboardingComplete: session?.onboarding_complete ?? false,
  };
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
            Open full dashboard
          </h3>
        </div>
        <span className="border border-black bg-white px-2 py-1 text-[9px] font-black uppercase tracking-[0.18em]">
          {profile.onboardingComplete ? "Ready" : "In Progress"}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <span className="border border-black bg-white px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em]">
          Persona: {profile.persona}
        </span>
        <span className="border border-black bg-white px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em]">
          Goal: {profile.goal}
        </span>
        <span className="border border-black bg-white px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em]">
          Lane: {profile.currentLane}
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

function QuickAccessSection({
  products,
  latestAssistantMessage,
  onQuickSend,
}: {
  products: string[];
  latestAssistantMessage: ChatMessage | null;
  onQuickSend: (query: string) => void;
}) {
  const chips = (latestAssistantMessage?.chips || []).slice(0, 2);

  return (
    <section className="border-2 border-black bg-[#DDE7FF] p-3 shadow-[4px_4px_0px_0px_black]">
      <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#1040C0]">
        Quick Access
      </p>

      <div className="mt-3 grid grid-cols-2 gap-2">
        {products.slice(0, 4).map((product) => (
          <a
            key={product}
            href={PRODUCT_LINKS[product]}
            target="_blank"
            rel="noreferrer"
            className="group flex min-h-[58px] items-center justify-between border-2 border-black bg-white px-3 py-2 shadow-[3px_3px_0px_0px_black] transition-transform hover:-translate-y-0.5"
          >
            <span className="text-[10px] font-black uppercase leading-4">{product}</span>
            <span className="text-[12px] font-black text-[#1040C0] transition-transform group-hover:translate-x-1">
              →
            </span>
          </a>
        ))}
      </div>

      {chips.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {chips.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => onQuickSend(chip)}
              className="border border-black bg-white px-2.5 py-1.5 text-[10px] font-black uppercase tracking-[0.14em]"
            >
              {chip}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function LiveContextSection({
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
  const liveContext = buildLiveContextSummary(latestAssistantMessage, session);
  const showMarketSnapshot =
    !!marketSnapshot &&
    ["markets_tools", "portfolio_view"].includes(latestAssistantMessage?.visualHint || "");

  return (
    <section className="border-2 border-black bg-[#FFE6E6] p-3 shadow-[4px_4px_0px_0px_black]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020]">
            Live Context
          </p>
          <h3 className="mt-1 text-sm font-black uppercase">
            {showMarketSnapshot ? "Market Snapshot" : liveContext.title}
          </h3>
        </div>
        <span className="border border-black bg-white px-2 py-1 text-[9px] font-black uppercase tracking-[0.18em]">
          {showMarketSnapshot ? "Live" : "Luna"}
        </span>
      </div>

      {showMarketSnapshot ? (
        <div className="mt-3">
          <MarketSnapshotPanel snapshot={marketSnapshot} />
        </div>
      ) : marketSnapshotLoading ? (
        <div className="mt-3 border-2 border-black bg-white px-3 py-4 shadow-[3px_3px_0px_0px_black]">
          <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#D02020]">
            Pulling live context
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
      ) : (
        <div className="mt-3 border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]">
          <p className="text-[11px] font-black uppercase">{liveContext.title}</p>
          <p className="mt-2 text-[12px] font-medium leading-5 text-black/75">
            {liveContext.summary}
          </p>
          {liveContext.bullets.length > 0 ? (
            <div className="mt-3 space-y-1.5">
              {liveContext.bullets.slice(0, 2).map((item) => (
                <p
                  key={item}
                  className="text-[10px] font-black uppercase tracking-[0.16em] text-[#1040C0]"
                >
                  {item}
                </p>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </section>
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
  if (!visible) return null;

  const useNowProducts = buildUseNowProducts(
    latestAssistantMessage?.recommendedProducts || [],
    session
  );
  const nextActions = buildNextActions(latestAssistantMessage);

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
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <div className="space-y-3">
            <ProfileGatewaySection
              latestAssistantMessage={latestAssistantMessage}
              session={session}
            />

            <QuickAccessSection
              products={useNowProducts}
              latestAssistantMessage={latestAssistantMessage}
              onQuickSend={onQuickSend}
            />

            <LiveContextSection
              latestAssistantMessage={latestAssistantMessage}
              marketSnapshot={marketSnapshot}
              marketSnapshotLoading={marketSnapshotLoading}
              session={session}
            />

            {nextActions.roadmapSteps.length > 0 ? (
              <section className="border-2 border-black bg-[#E7F7EA] p-3 shadow-[4px_4px_0px_0px_black]">
                <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#163A21]">
                  Next Best Action
                </p>
                <div className="mt-3 space-y-2">
                  {nextActions.roadmapSteps.map((step) => (
                    <button
                      key={`${step.step}-${step.product}`}
                      type="button"
                      onClick={() => onQuickSend(`Help me explore ${step.product}`)}
                      className="flex w-full items-start gap-2 border-2 border-black bg-white px-3 py-2.5 text-left shadow-[3px_3px_0px_0px_black]"
                    >
                      <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center border-2 border-black bg-[#F0C020] text-[10px] font-black">
                        {step.step}
                      </span>
                      <span className="min-w-0">
                        <span className="block text-[10px] font-black uppercase">
                          {step.product}
                        </span>
                        <span className="mt-1 block text-[10px] font-medium leading-4 text-black/75">
                          {step.reason}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              </section>
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
