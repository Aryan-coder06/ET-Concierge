'use client';

import type {
  MarketSnapshot,
  SourceCitation,
  VisualHint,
} from "@/components/search/types";

type InsightLink = {
  label: string;
  href: string;
  note: string;
};

type WidgetSpec = {
  title: string;
  value: string;
  detail: string;
  accentClassName: string;
  graph: number[];
};

type Props = {
  visualHint?: string | null;
  sourceCitations?: SourceCitation[];
  recommendedProducts?: string[];
  marketSnapshot?: MarketSnapshot | null;
};

const PANEL_CONFIG: Record<
  VisualHint,
  {
    eyebrow: string;
    title: string;
    description: string;
    cardClassName: string;
    visualClassName: string;
  }
> = {
  ecosystem_map: {
    eyebrow: "Visual Assist",
    title: "ET ecosystem map",
    description:
      "This query is better understood with product lanes, so Luna is surfacing the core ET entry points beside the answer.",
    cardClassName: "bg-[#FFF6CC]",
    visualClassName: "bg-[#121212] text-white",
  },
  trust_signal: {
    eyebrow: "Verification Mode",
    title: "Trust and policy checks",
    description:
      "This answer carries verification risk, so the UI highlights the exact ET pages you should double-check before acting.",
    cardClassName: "bg-[#FFD9D9]",
    visualClassName: "bg-[#3A0909] text-white",
  },
  markets_tools: {
    eyebrow: "Live Tools",
    title: "Markets signal panel",
    description:
      "For market or trading queries, Luna can pair the answer with direct ET tool paths instead of only returning text.",
    cardClassName: "bg-[#DDE7FF]",
    visualClassName: "bg-[#0D225E] text-white",
  },
  portfolio_view: {
    eyebrow: "Portfolio Mode",
    title: "Tracking and goal view",
    description:
      "Portfolio questions are easier to understand with a monitoring-style panel, so the UI points to ET tracking surfaces.",
    cardClassName: "bg-[#E7F7EA]",
    visualClassName: "bg-[#163A21] text-white",
  },
  learning_lane: {
    eyebrow: "Learning Lane",
    title: "Structured learning path",
    description:
      "When the user is exploring learning, Luna can show a guided lane instead of leaving the answer as a plain paragraph.",
    cardClassName: "bg-[#FFF0D6]",
    visualClassName: "bg-[#4C2C08] text-white",
  },
  events_network: {
    eyebrow: "Network View",
    title: "Events and community map",
    description:
      "Event queries are more useful when the answer also exposes ET's active portals and connected discovery paths.",
    cardClassName: "bg-[#F1DEFF]",
    visualClassName: "bg-[#31104F] text-white",
  },
};

const PREFERRED_SOURCE_IDS: Record<VisualHint, string[]> = {
  ecosystem_map: [
    "et_prime_faq",
    "et_markets_google_play",
    "et_portfolio_home",
    "et_masterclass_home",
    "et_b2b_events",
    "et_benefits",
  ],
  trust_signal: ["et_prime_faq", "et_terms", "et_benefits"],
  markets_tools: ["market_mood", "stock_reports_plus", "et_markets_google_play"],
  portfolio_view: ["et_portfolio_home", "et_portfolio_mobile", "et_markets_google_play"],
  learning_lane: ["et_masterclass_home", "et_prime_faq"],
  events_network: [
    "et_b2b_events",
    "enterprise_ai_events",
    "cio_events",
    "bfsi_events",
    "government_events",
  ],
};

const FALLBACK_LINKS: Record<VisualHint, InsightLink[]> = {
  ecosystem_map: [
    {
      label: "ET Prime",
      href: "https://economictimes.indiatimes.com/prime/about-us",
      note: "Broad ET entry point",
    },
    {
      label: "ET Markets",
      href: "https://economictimes.indiatimes.com/markets",
      note: "Markets and discovery lane",
    },
    {
      label: "ET Portfolio",
      href: "https://etportfolio.economictimes.indiatimes.com/",
      note: "Tracking and goals",
    },
    {
      label: "ETMasterclass",
      href: "https://masterclass.economictimes.indiatimes.com/",
      note: "Learning and workshops",
    },
  ],
  trust_signal: [
    {
      label: "ET Prime FAQ",
      href: "https://economictimes.indiatimes.com/prime/faq",
      note: "Official help and access checks",
    },
    {
      label: "ET Terms",
      href: "https://economictimes.indiatimes.com/terms-conditions",
      note: "Terms and policy verification",
    },
    {
      label: "ET Benefits",
      href: "https://economictimes.indiatimes.com/et_benefits.cms?from=mdr",
      note: "Prime-linked benefits lane",
    },
  ],
  markets_tools: [
    {
      label: "Market Mood",
      href: "https://economictimes.indiatimes.com/markets/stock-market-mood",
      note: "Sentiment and market pulse",
    },
    {
      label: "Stock Reports Plus",
      href: "https://economictimes.indiatimes.com/markets/benefits/stockreportsplus",
      note: "Stock research lane",
    },
    {
      label: "ET Markets App",
      href: "https://play.google.com/store/apps/details?hl=en_IN&id=com.et.market",
      note: "Mobile markets access",
    },
  ],
  portfolio_view: [
    {
      label: "ET Portfolio",
      href: "https://etportfolio.economictimes.indiatimes.com/",
      note: "Desktop tracking lane",
    },
    {
      label: "Portfolio Mobile",
      href: "https://m.economictimes.com/pf_portfoliohome.cms",
      note: "Mobile portfolio surface",
    },
    {
      label: "ET Markets",
      href: "https://economictimes.indiatimes.com/markets",
      note: "Pair discovery with tracking",
    },
  ],
  learning_lane: [
    {
      label: "ETMasterclass",
      href: "https://masterclass.economictimes.indiatimes.com/",
      note: "Courses and workshops",
    },
    {
      label: "ET Prime",
      href: "https://economictimes.indiatimes.com/prime/about-us",
      note: "Deeper context layer",
    },
  ],
  events_network: [
    {
      label: "ET B2B Events",
      href: "https://b2b.economictimes.indiatimes.com/events",
      note: "Business event hub",
    },
    {
      label: "Enterprise AI",
      href: "https://enterpriseai.economictimes.indiatimes.com/events",
      note: "AI event lane",
    },
    {
      label: "CIO Events",
      href: "https://cio.economictimes.indiatimes.com/events",
      note: "Technology leadership",
    },
    {
      label: "BFSI Events",
      href: "https://bfsi.economictimes.indiatimes.com/events",
      note: "Finance and BFSI events",
    },
  ],
};

function dedupeLinks(links: InsightLink[]) {
  const seen = new Set<string>();
  const unique: InsightLink[] = [];

  for (const link of links) {
    const key = link.href;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(link);
  }

  return unique;
}

function buildInsightLinks(
  visualHint: VisualHint,
  sourceCitations: SourceCitation[],
  marketSnapshot?: MarketSnapshot | null
) {
  if (
    marketSnapshot &&
    marketSnapshot.etLinks.length > 0 &&
    (visualHint === "markets_tools" || visualHint === "portfolio_view")
  ) {
    return dedupeLinks(
      marketSnapshot.etLinks.map((link) => ({
        label: link.label,
        href: link.href,
        note: link.note,
      }))
    ).slice(0, 4);
  }

  const preferredIds = new Set(PREFERRED_SOURCE_IDS[visualHint]);
  const fromCitations = sourceCitations
    .filter((citation) => citation.href && citation.sourceId && preferredIds.has(citation.sourceId))
    .map(
      (citation) =>
        ({
          label: citation.label,
          href: citation.href!,
          note:
            [citation.pageType, citation.verificationStatus].filter(Boolean).join(" · ") ||
            "Official ET source",
        }) satisfies InsightLink
    );

  return dedupeLinks([...fromCitations, ...FALLBACK_LINKS[visualHint]]).slice(0, 4);
}

function buildWidgets(
  visualHint: VisualHint,
  recommendedProducts: string[],
  marketSnapshot?: MarketSnapshot | null
) {
  const primary = recommendedProducts[0] || "ET";

  if (
    marketSnapshot &&
    marketSnapshot.items.length > 0 &&
    (visualHint === "markets_tools" || visualHint === "portfolio_view")
  ) {
    return marketSnapshot.items.slice(0, 3).map((item) => ({
      title: item.label,
      value: `${item.price.toLocaleString("en-IN", {
        maximumFractionDigits: 2,
      })}`,
      detail: `${item.change >= 0 ? "+" : ""}${item.change.toFixed(2)} (${item.changePct >= 0 ? "+" : ""}${item.changePct.toFixed(2)}%) · ${item.etRoute}`,
      accentClassName:
        item.change > 0
          ? "bg-[#1040C0]"
          : item.change < 0
            ? "bg-[#D02020]"
            : "bg-[#121212]",
      graph: item.sparkline.length > 1 ? item.sparkline : [item.price, item.price, item.price],
    }));
  }

  const byHint: Record<VisualHint, WidgetSpec[]> = {
    ecosystem_map: [
      {
        title: "Primary lane",
        value: primary,
        detail: "Broadest ET entry point for this question",
        accentClassName: "bg-[#D02020]",
        graph: [16, 24, 20, 30, 34, 40],
      },
      {
        title: "Path count",
        value: `${Math.max(recommendedProducts.length, 4)} lanes`,
        detail: "Main ET surfaces Luna wants to expose here",
        accentClassName: "bg-[#1040C0]",
        graph: [10, 14, 18, 24, 22, 28],
      },
      {
        title: "Mode",
        value: "Discovery",
        detail: "This answer benefits from a product-map view",
        accentClassName: "bg-[#F0C020]",
        graph: [8, 12, 18, 16, 22, 30],
      },
    ],
    trust_signal: [
      {
        title: "Check now",
        value: "FAQ / Terms",
        detail: "Use official pages before acting on trial or benefit claims",
        accentClassName: "bg-[#D02020]",
        graph: [28, 24, 22, 16, 20, 18],
      },
      {
        title: "Risk mode",
        value: "Caution",
        detail: "This answer may depend on current public ET signals",
        accentClassName: "bg-[#121212]",
        graph: [16, 12, 18, 12, 14, 10],
      },
      {
        title: "Next action",
        value: "Verify live page",
        detail: "Cross-check checkout, terms, or activation rules",
        accentClassName: "bg-[#F0C020]",
        graph: [12, 16, 20, 22, 18, 24],
      },
    ],
    markets_tools: [
      {
        title: "Signal lane",
        value: "Market Mood",
        detail: "Sentiment and mood tracker for market direction",
        accentClassName: "bg-[#1040C0]",
        graph: [10, 18, 14, 24, 22, 32, 28],
      },
      {
        title: "Research lane",
        value: "Reports+",
        detail: "Stock research surface with sharper company context",
        accentClassName: "bg-[#D02020]",
        graph: [12, 20, 18, 26, 30, 36, 40],
      },
      {
        title: "Best fit",
        value: "Active discovery",
        detail: "This answer is better with tools than plain reading",
        accentClassName: "bg-[#F0C020]",
        graph: [14, 16, 24, 22, 30, 28, 34],
      },
    ],
    portfolio_view: [
      {
        title: "Tracking lane",
        value: "Holdings",
        detail: "Portfolio questions benefit from a monitor-style view",
        accentClassName: "bg-[#163A21]",
        graph: [18, 20, 24, 26, 28, 30],
      },
      {
        title: "Goal lane",
        value: "SIP + alerts",
        detail: "Goal-linked nudges and portfolio updates",
        accentClassName: "bg-[#F0C020]",
        graph: [10, 14, 18, 24, 26, 32],
      },
      {
        title: "Companion",
        value: "ET Markets",
        detail: "Discovery and tracking usually work better together",
        accentClassName: "bg-[#1040C0]",
        graph: [12, 18, 16, 22, 20, 26],
      },
    ],
    learning_lane: [
      {
        title: "Learning mode",
        value: "Structured",
        detail: "The user likely needs a guided track, not just an article",
        accentClassName: "bg-[#4C2C08]",
        graph: [10, 12, 18, 24, 28, 36],
      },
      {
        title: "Best lane",
        value: "ETMasterclass",
        detail: "Use workshops and curated learning paths",
        accentClassName: "bg-[#D02020]",
        graph: [8, 14, 20, 22, 30, 34],
      },
      {
        title: "Support layer",
        value: "ET Prime",
        detail: "Prime adds broader context around the learning path",
        accentClassName: "bg-[#F0C020]",
        graph: [12, 18, 22, 26, 24, 30],
      },
    ],
    events_network: [
      {
        title: "Network mode",
        value: "Events hubs",
        detail: "This answer fits better with portal-level discovery",
        accentClassName: "bg-[#31104F]",
        graph: [12, 18, 24, 20, 26, 34],
      },
      {
        title: "Community lane",
        value: "Industry touchpoints",
        detail: "Use ET event portals for live discovery and registration",
        accentClassName: "bg-[#D02020]",
        graph: [10, 16, 18, 26, 24, 30],
      },
      {
        title: "Best starting point",
        value: "ET Events",
        detail: "Strong fit for summit, conference, and portal questions",
        accentClassName: "bg-[#F0C020]",
        graph: [14, 20, 24, 30, 34, 38],
      },
    ],
  };

  return byHint[visualHint];
}

function accentColor(accentClassName: string) {
  if (accentClassName === "bg-[#1040C0]") return "#1040C0";
  if (accentClassName === "bg-[#F0C020]") return "#F0C020";
  if (accentClassName === "bg-[#163A21]") return "#163A21";
  if (accentClassName === "bg-[#31104F]") return "#31104F";
  if (accentClassName === "bg-[#121212]") return "#121212";
  if (accentClassName === "bg-[#4C2C08]") return "#4C2C08";
  return "#D02020";
}

function Sparkline({ points, accentClassName }: { points: number[]; accentClassName: string }) {
  const maxPoint = Math.max(...points);
  const color = accentColor(accentClassName);
  const polylinePoints = points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * 100;
      const y = 32 - (point / maxPoint) * 24;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox="0 0 100 32" className="mt-3 h-10 w-full overflow-visible" fill="none">
      <polyline
        points={polylinePoints}
        className="insight-trace"
        stroke={color}
        strokeWidth="2.5"
        vectorEffect="non-scaling-stroke"
      />
      {points.map((point, index) => {
        const x = (index / Math.max(points.length - 1, 1)) * 100;
        const y = 32 - (point / maxPoint) * 24;
        return (
          <circle
            key={`${accentClassName}-${point}-${index}`}
            cx={x}
            cy={y}
            r="2.4"
            fill={color}
          />
        );
      })}
    </svg>
  );
}

function InsightMiniVisual({ visualHint }: { visualHint: VisualHint }) {
  if (visualHint === "markets_tools") {
    return (
      <div className="flex h-full items-end gap-2">
        {[36, 58, 84, 62, 92].map((height, index) => (
          <span
            key={`${visualHint}-${height}`}
            className={`signal-bar w-7 border-2 border-white ${
              index % 2 === 0 ? "bg-[#F0C020]" : index === 1 ? "bg-[#D02020]" : "bg-white"
            }`}
            style={{ height: `${height}px`, animationDelay: `${index * 0.12}s` }}
          />
        ))}
      </div>
    );
  }

  if (visualHint === "portfolio_view") {
    return (
      <div className="relative flex h-full items-center justify-center">
        <div className="insight-pulse-ring absolute h-24 w-24 rounded-full border-2 border-[#F0C020]" />
        <div className="absolute h-16 w-16 rounded-full border-2 border-white" />
        <div className="absolute h-8 w-8 rounded-full bg-[#F0C020]" />
        <div className="absolute bottom-4 left-4 right-4 flex items-end gap-2">
          {[24, 34, 48, 38].map((height, index) => (
            <span
              key={`${visualHint}-${height}`}
              className="signal-bar flex-1 bg-white/85"
              style={{ height: `${height}px`, animationDelay: `${index * 0.14}s` }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (visualHint === "learning_lane") {
    return (
      <div className="flex h-full items-end gap-3">
        {[1, 2, 3].map((step) => (
          <div
            key={`${visualHint}-${step}`}
            className="insight-float flex w-16 flex-col justify-end border-2 border-white bg-white/12 p-2"
            style={{ height: `${76 + step * 18}px`, animationDelay: `${step * 0.16}s` }}
          >
            <span className="text-[9px] font-black uppercase tracking-[0.2em] text-[#F0C020]">
              Step {step}
            </span>
            <span className="mt-2 block h-2 w-full bg-white" />
          </div>
        ))}
      </div>
    );
  }

  if (visualHint === "events_network") {
    return (
      <div className="relative h-full w-full">
        <div className="absolute h-px w-24 bg-white/70" style={{ left: "48px", top: "28px" }} />
        <div className="absolute h-24 w-px bg-white/70" style={{ left: "144px", top: "28px" }} />
        <div className="absolute h-px w-24 bg-white/70" style={{ left: "48px", top: "124px" }} />
        {[
          { left: "14px", top: "12px" },
          { left: "110px", top: "12px" },
          { left: "110px", top: "108px" },
          { left: "206px", top: "108px" },
        ].map((position, index) => (
          <span
            key={`${visualHint}-${position.left}-${position.top}`}
            className={`insight-node absolute h-8 w-8 rounded-full border-2 border-white ${
              index % 2 === 0 ? "bg-[#F0C020]" : "bg-[#D02020]"
            }`}
            style={{
              left: position.left,
              top: position.top,
              animationDelay: `${index * 0.12}s`,
            }}
          />
        ))}
      </div>
    );
  }

  if (visualHint === "trust_signal") {
    return (
      <div className="relative flex h-full items-center justify-center">
        <div className="insight-pulse-ring absolute h-28 w-28 rounded-full border-2 border-[#FFD6D6]" />
        <div className="absolute flex w-[120px] flex-col gap-2">
          {["Current page", "FAQ / Terms", "Activation check"].map((label, index) => (
            <div
              key={`${visualHint}-${label}`}
              className="insight-float border border-white bg-white/14 px-3 py-2"
              style={{ animationDelay: `${index * 0.12}s` }}
            >
              <span className="text-[9px] font-black uppercase tracking-[0.22em] text-white">
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <div className="absolute left-5 top-5 h-12 w-20 border-2 border-white bg-[#D02020]" />
      <div className="absolute right-5 top-5 h-12 w-20 border-2 border-white bg-[#1040C0]" />
      <div className="absolute left-1/2 top-[46%] h-14 w-24 -translate-x-1/2 -translate-y-1/2 border-2 border-white bg-[#F0C020]" />
      <div className="absolute h-px w-24 bg-white/80" style={{ left: "64px", top: "68px" }} />
      <div className="absolute h-px w-24 bg-white/80" style={{ right: "64px", top: "68px" }} />
      <div className="absolute left-1/2 top-[54%] h-14 w-px -translate-x-1/2 bg-white/80" />
      {[
        { left: "20px", top: "16px" },
        { left: "216px", top: "16px" },
        { left: "128px", top: "42px" },
      ].map((position, index) => (
          <span
            key={`${visualHint}-${position.left}-${position.top}`}
            className={`insight-node absolute h-6 w-6 rounded-full border-2 border-white ${
              index === 0 ? "bg-[#D02020]" : index === 1 ? "bg-[#1040C0]" : "bg-[#F0C020]"
            }`}
            style={{
              left: position.left,
              top: position.top,
              animationDelay: `${index * 0.1}s`,
            }}
          />
        )
      )}
    </div>
  );
}

export function ResponseInsightPanel({
  visualHint,
  sourceCitations = [],
  recommendedProducts = [],
  marketSnapshot,
}: Props) {
  if (!visualHint || !(visualHint in PANEL_CONFIG)) {
    return null;
  }

  const safeHint = visualHint as VisualHint;
  const config = PANEL_CONFIG[safeHint];
  const links = buildInsightLinks(safeHint, sourceCitations, marketSnapshot);
  const widgets = buildWidgets(safeHint, recommendedProducts, marketSnapshot);

  return (
    <div className={`mt-3 overflow-hidden border-2 border-black ${config.cardClassName}`}>
      <div className="grid gap-3 p-3 md:grid-cols-[168px_minmax(0,1fr)]">
        <div className={`min-h-[152px] border-2 border-black p-3 ${config.visualClassName}`}>
          <p className="text-[9px] font-black uppercase tracking-[0.24em] text-white/70">
            Live visual
          </p>
          <div className="mt-3 h-[106px]">
            <InsightMiniVisual visualHint={safeHint} />
          </div>
        </div>

        <div className="min-w-0">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020]">
            {config.eyebrow}
          </p>
          <h4 className="mt-1 font-black uppercase text-base sm:text-lg">{config.title}</h4>
          <p className="mt-2 max-w-2xl text-[13px] font-medium leading-6 sm:text-sm">
            {config.description}
          </p>

          {recommendedProducts.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {recommendedProducts.slice(0, 4).map((product) => (
                <span
                  key={`${safeHint}-${product}`}
                  className="border border-black bg-white px-2 py-1 text-[10px] font-black uppercase tracking-wide"
                >
                  {product}
                </span>
              ))}
            </div>
          ) : null}

          <div className="mt-3 grid gap-2 lg:grid-cols-3">
            {widgets.map((widget) => (
              <div
                key={`${safeHint}-${widget.title}`}
                className="border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]"
              >
                <span className={`block h-1.5 w-16 ${widget.accentClassName}`} />
                <div className="mt-3 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-black uppercase tracking-[0.18em] text-black/58">
                      {widget.title}
                    </p>
                    <p className="mt-1 text-sm font-black uppercase">{widget.value}</p>
                  </div>
                  <span className="text-[9px] font-black uppercase tracking-[0.18em] text-black/45">
                    Live now
                  </span>
                </div>
                <Sparkline points={widget.graph} accentClassName={widget.accentClassName} />
                <p className="mt-2 text-[11px] font-medium leading-5 text-black/70">
                  {widget.detail}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {links.map((link) => (
              <a
                key={`${safeHint}-${link.href}-${link.label}`}
                href={link.href}
                target="_blank"
                rel="noreferrer"
                className="group border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black] transition-transform hover:-translate-y-0.5"
              >
                <span className="block text-[11px] font-black uppercase tracking-[0.16em]">
                  {link.label}
                </span>
                <span className="mt-1 block text-[11px] font-medium leading-5 text-black/68">
                  {link.note}
                </span>
                <span className="mt-2 inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.18em] text-[#1040C0]">
                  Open link
                  <span aria-hidden="true" className="transition-transform group-hover:translate-x-1">
                    →
                  </span>
                </span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
