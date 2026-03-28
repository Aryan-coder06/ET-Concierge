"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ConciergeRail } from "@/components/search/ConciergeRail";
import { LunaThinkingPanel } from "@/components/search/LunaThinkingPanel";
import { ResponseInsightPanel } from "@/components/search/ResponseInsightPanel";
import { ThreadRail } from "@/components/search/ThreadRail";
import type {
  AnswerStyle,
  BulletGroup,
  ChatMessage,
  ComparisonRow,
  DecisionSummary,
  JourneyEvent,
  MarketSnapshot,
  NavigatorSummary,
  ProfileSnapshot,
  ResponsePresentation,
  Roadmap,
  RoadmapStep,
  SessionDocument,
  SourceCitation,
  SourceItem,
  ThreadSummary,
  UiModule,
} from "@/components/search/types";
import { etCompassContent } from "@/content/etCompassContent";
import { getApiBaseUrl, getApiConfigurationError } from "@/lib/api-base-url";

type JsonRecord = Record<string, unknown>;

const STORAGE_KEY = "et-compass-luna-chat-state";
const API_CHAT_PATH = "/chat";

const SHELL_HEADER_H = 68;
const THREAD_RAIL_W = 280;
const CONTROL_RAIL_W = 320;

function uid() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function formatTime(value: string) {
  try {
    return new Date(value).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

function makeThreadTitle(text: string) {
  const clean = text.replace(/\s+/g, " ").trim();
  if (!clean) return "New thread";
  return clean.length > 34 ? `${clean.slice(0, 34)}...` : clean;
}

function getInitialAssistantMessage(): ChatMessage {
  return {
    id: uid(),
    role: "assistant",
    content: etCompassContent.searchPage.emptyStateDescription,
    createdAt: new Date().toISOString(),
  };
}

function isJsonRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null;
}

function readString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function extractTextFromResponse(data: unknown): string {
  if (typeof data === "string") return data;
  if (!isJsonRecord(data)) {
    return "Received a response from the server, but no readable answer field was found.";
  }

  const nestedData = isJsonRecord(data.data) ? data.data : undefined;

  const candidates = [
    data.answer,
    data.response,
    data.message,
    data.output,
    data.text,
    data.result,
    nestedData?.answer,
    nestedData?.response,
  ];

  for (const item of candidates) {
    const text = readString(item);
    if (text) return text;
  }

  return "Received a response from the server, but no readable answer field was found.";
}

function extractSources(data: unknown): SourceItem[] {
  if (!isJsonRecord(data)) return [];

  const raw = data.sources ?? data.citations ?? data.references ?? [];
  if (!Array.isArray(raw)) return [];

  return raw
    .map((item) => {
      if (typeof item === "string") return { label: item };

      if (isJsonRecord(item)) {
        const label =
          readString(item.label) ||
          readString(item.title) ||
          readString(item.name) ||
          readString(item.source) ||
          readString(item.url) ||
          "Source";
        const href = readString(item.href) || readString(item.url);

        return {
          label,
          href,
        };
      }

      return null;
    })
    .filter((item): item is SourceItem => item !== null);
}

function extractStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];

  return value
    .map((item) => readString(item))
    .filter((item): item is string => Boolean(item));
}

function extractSourceCitations(data: unknown): SourceCitation[] {
  if (!isJsonRecord(data) || !Array.isArray(data.source_citations)) return [];

  const citations: SourceCitation[] = [];

  for (const item of data.source_citations) {
    if (!isJsonRecord(item)) continue;

    citations.push({
      label:
        readString(item.label) ||
        readString(item.title) ||
        readString(item.source_id) ||
        readString(item.href) ||
        "ET Source",
      href: readString(item.href) || readString(item.url),
      sourceId: readString(item.source_id) || readString(item.sourceId),
      verificationStatus:
        readString(item.verification_status) || readString(item.verificationStatus),
      pageType: readString(item.page_type) || readString(item.pageType),
    });
  }

  return citations;
}

function extractRoadmap(data: unknown): Roadmap | undefined {
  if (!isJsonRecord(data) || !isJsonRecord(data.roadmap)) return undefined;

  const rawSteps = Array.isArray(data.roadmap.steps) ? data.roadmap.steps : [];
  const steps: RoadmapStep[] = [];

  for (const item of rawSteps) {
    if (!isJsonRecord(item)) continue;
    const product = readString(item.product);
    const reason = readString(item.reason);
    if (!product || !reason) continue;

    const rawStep = item.step;
    const stepNumber =
      typeof rawStep === "number"
        ? rawStep
        : typeof rawStep === "string"
          ? Number.parseInt(rawStep, 10)
          : NaN;

    if (!Number.isFinite(stepNumber) || stepNumber <= 0) continue;

    steps.push({
      step: stepNumber,
      product,
      reason,
      url: readString(item.url),
    });
  }

  const title = readString(data.roadmap.title);
  if (!title && steps.length === 0) return undefined;

  return {
    title: title || "Your ET roadmap",
    profile_summary: extractStringArray(data.roadmap.profile_summary),
    steps,
  };
}

function extractNavigatorSummary(data: unknown): NavigatorSummary | null {
  if (!isJsonRecord(data) || !isJsonRecord(data.navigator_summary)) return null;

  const title = readString(data.navigator_summary.title);
  const summary = readString(data.navigator_summary.summary);
  if (!title || !summary) return null;

  return {
    title,
    summary,
    why_this_path: extractStringArray(data.navigator_summary.why_this_path),
    next_move: readString(data.navigator_summary.next_move),
  };
}

function extractProfileSnapshot(value: unknown): ProfileSnapshot {
  if (!isJsonRecord(value)) return {};

  return {
    name: readString(value.name),
    intent: readString(value.intent),
    sophistication: readString(value.sophistication),
    goal: readString(value.goal),
    profession: readString(value.profession),
    age_range: readString(value.age_range),
    interests: extractStringArray(value.interests),
    existing_products: extractStringArray(value.existing_products),
    onboarding_complete:
      typeof value.onboarding_complete === "boolean" ? value.onboarding_complete : undefined,
  };
}

function extractComparisonRows(value: unknown): ComparisonRow[] {
  if (!isJsonRecord(value) || !Array.isArray(value.comparison_rows)) return [];

  return value.comparison_rows
    .map((item) => {
      if (!isJsonRecord(item)) return null;
      const row: ComparisonRow = {
        item: readString(item.item) || "",
        best_for: readString(item.best_for) || "",
        why: readString(item.why) || "",
      };
      if (!row.item || !row.best_for || !row.why) return null;
      return row;
    })
    .filter((item): item is ComparisonRow => Boolean(item));
}

function extractBulletGroups(value: unknown): BulletGroup[] {
  if (!isJsonRecord(value) || !Array.isArray(value.bullet_groups)) return [];

  return value.bullet_groups
    .map((item) => {
      if (!isJsonRecord(item)) return null;
      const title = readString(item.title);
      const items = extractStringArray(item.items);
      if (!title || items.length === 0) return null;
      return { title, items };
    })
    .filter((item): item is BulletGroup => Boolean(item));
}

function extractDecision(value: unknown): DecisionSummary | null {
  if (!isJsonRecord(value) || !isJsonRecord(value.decision)) return null;
  const raw = value.decision;

  const primary = isJsonRecord(raw.primary_recommendation)
    ? {
        product: readString(raw.primary_recommendation.product),
        display_product: readString(raw.primary_recommendation.display_product),
        why: extractStringArray(raw.primary_recommendation.why),
        confidence: readString(raw.primary_recommendation.confidence),
      }
    : undefined;

  const secondary = Array.isArray(raw.secondary_recommendations)
    ? raw.secondary_recommendations
        .map((item) => {
          if (!isJsonRecord(item)) return null;
          return {
            product: readString(item.product),
            display_product: readString(item.display_product),
            why: extractStringArray(item.why),
          };
        })
        .filter(Boolean) as NonNullable<DecisionSummary["secondary_recommendations"]>
    : [];

  const nextBestAction = isJsonRecord(raw.next_best_action)
    ? {
        label: readString(raw.next_best_action.label),
        href: readString(raw.next_best_action.href),
        reason: readString(raw.next_best_action.reason),
      }
    : undefined;

  const scoredProducts = Array.isArray(raw.scored_products)
    ? raw.scored_products
        .map((item) => {
          if (!isJsonRecord(item)) return null;
          return {
            product: readString(item.product),
            display_product: readString(item.display_product),
            score: typeof item.score === "number" ? item.score : Number(item.score),
            reasons: extractStringArray(item.reasons),
          };
        })
        .filter((item) => Boolean(item?.product)) as NonNullable<DecisionSummary["scored_products"]>
    : [];

  return {
    primary_recommendation: primary,
    secondary_recommendations: secondary,
    current_lane: readString(raw.current_lane),
    next_best_action: nextBestAction,
    scored_products: scoredProducts,
    signals: extractStringArray(raw.signals),
  };
}

function extractUiModules(value: unknown): UiModule[] {
  if (!isJsonRecord(value) || !Array.isArray(value.ui_modules)) return [];

  return value.ui_modules
    .map((item) => {
      if (!isJsonRecord(item)) return null;
      return {
        module_type: readString(item.module_type) || "recommendation_card",
        visible: typeof item.visible === "boolean" ? item.visible : undefined,
        priority: typeof item.priority === "number" ? item.priority : Number(item.priority),
        payload: isJsonRecord(item.payload) ? item.payload : undefined,
      };
    })
    .filter(Boolean) as UiModule[];
}

function extractPresentation(value: unknown): ResponsePresentation | null {
  if (!isJsonRecord(value)) return null;

  return {
    answer_style: readString(value.answer_style) as AnswerStyle | string | undefined,
    show_visual_panel:
      typeof value.show_visual_panel === "boolean" ? value.show_visual_panel : undefined,
    show_recommended_products:
      typeof value.show_recommended_products === "boolean"
        ? value.show_recommended_products
        : undefined,
    show_navigator_summary:
      typeof value.show_navigator_summary === "boolean"
        ? value.show_navigator_summary
        : undefined,
    show_roadmap:
      typeof value.show_roadmap === "boolean" ? value.show_roadmap : undefined,
    show_chips:
      typeof value.show_chips === "boolean" ? value.show_chips : undefined,
  };
}

function extractJourneyEvent(value: unknown): JourneyEvent | null {
  if (!isJsonRecord(value)) return null;

  const navigatorSummary = isJsonRecord(value.navigator_summary)
    ? {
        navigator_summary: value.navigator_summary,
      }
    : undefined;
  const roadmap = isJsonRecord(value.roadmap)
    ? {
        roadmap: value.roadmap,
      }
    : undefined;

  return {
    timestamp: readString(value.timestamp),
    route: readString(value.route),
    user_message: readString(value.user_message),
    assistant_message: readString(value.assistant_message),
    recommendations: extractStringArray(value.recommendations),
    recommended_products: extractStringArray(
      value.recommended_products ?? value.recommendations
    ),
    source_citations: Array.isArray(value.source_citations)
      ? extractSourceCitations({ source_citations: value.source_citations })
      : [],
    verification_notes: extractStringArray(value.verification_notes),
    navigator_summary: navigatorSummary ? extractNavigatorSummary(navigatorSummary) : null,
    roadmap: roadmap ? extractRoadmap(roadmap) : undefined,
    chips: extractStringArray(value.chips),
    visual_hint: readString(value.visual_hint),
    answer_style: readString(value.answer_style),
    presentation: extractPresentation(value.presentation),
    decision: extractDecision(value),
    comparison_rows: extractComparisonRows(value),
    bullet_groups: extractBulletGroups(value),
    ui_modules: extractUiModules(value),
    profile_snapshot: extractProfileSnapshot(value.profile_snapshot),
  };
}

function extractSessionDocument(data: unknown): SessionDocument | null {
  if (!isJsonRecord(data)) return null;

  const sessionId = readString(data.session_id);
  const title = readString(data.title);

  if (!sessionId || !title) return null;

  return {
    session_id: sessionId,
    title,
    profile: extractProfileSnapshot(data.profile),
    onboarding_complete: Boolean(data.onboarding_complete),
    questions_asked: extractStringArray(data.questions_asked),
    messages: Array.isArray(data.messages)
      ? data.messages
          .map((item) => {
            if (!isJsonRecord(item)) return null;
            const role = readString(item.role);
            const content = readString(item.content);
            if (!role || !content) return null;
            return { role, content };
          })
          .filter((item): item is { role: string; content: string } => Boolean(item))
      : [],
    journey_history: Array.isArray(data.journey_history)
      ? data.journey_history
          .map((item) => extractJourneyEvent(item))
          .filter((item): item is JourneyEvent => Boolean(item))
      : [],
    recommendations: extractStringArray(data.recommendations),
    recommended_products: extractStringArray(
      data.recommended_products ?? data.recommendations
    ),
    response_type: readString(data.response_type),
    updated_at: readString(data.updated_at),
  };
}

function extractMarketSnapshot(data: unknown): MarketSnapshot | null {
  if (!isJsonRecord(data)) return null;

  const asOf = readString(data.as_of);
  const sourceLabel = readString(data.source_label);
  if (!asOf || !sourceLabel) return null;

  const items = Array.isArray(data.items)
    ? data.items
        .map((item) => {
          if (!isJsonRecord(item)) return null;
          const symbol = readString(item.symbol);
          const label = readString(item.label);
          const href = readString(item.href);
          const etRoute = readString(item.et_route);
          const rawPrice = typeof item.price === "number" ? item.price : Number(item.price);
          const rawChange =
            typeof item.change === "number" ? item.change : Number(item.change);
          const rawChangePct =
            typeof item.change_pct === "number"
              ? item.change_pct
              : Number(item.change_pct);

          if (
            !symbol ||
            !label ||
            !href ||
            !etRoute ||
            !Number.isFinite(rawPrice) ||
            !Number.isFinite(rawChange) ||
            !Number.isFinite(rawChangePct)
          ) {
            return null;
          }

          return {
            symbol,
            label,
            href,
            etRoute,
            price: rawPrice,
            change: rawChange,
            changePct: rawChangePct,
            sparkline: Array.isArray(item.sparkline)
              ? item.sparkline
                  .map((point) => (typeof point === "number" ? point : Number(point)))
                  .filter((point) => Number.isFinite(point))
              : [],
          };
        })
        .filter(
          (item): item is MarketSnapshot["items"][number] =>
            Boolean(item)
        )
    : [];

  const etLinks = Array.isArray(data.et_links)
    ? data.et_links
        .map((item) => {
          if (!isJsonRecord(item)) return null;
          const label = readString(item.label);
          const href = readString(item.href);
          const note = readString(item.note);
          if (!label || !href || !note) return null;
          return { label, href, note };
        })
        .filter(
          (item): item is MarketSnapshot["etLinks"][number] =>
            Boolean(item)
        )
    : [];

  return {
    asOf,
    sourceLabel,
    items,
    etLinks,
  };
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 7h16" />
      <path d="M4 12h16" />
      <path d="M4 17h16" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M6 6l12 12" />
      <path d="M18 6 6 18" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
      <path d="M3.4 20.4 21 12 3.4 3.6 3.3 10l12.2 2-12.2 2 .1 6.4Z" />
    </svg>
  );
}

export default function SearchPage() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [messagesByThread, setMessagesByThread] = useState<Record<string, ChatMessage[]>>({});
  const [activeThreadId, setActiveThreadId] = useState("");
  const [activeSession, setActiveSession] = useState<SessionDocument | null>(null);
  const [marketSnapshot, setMarketSnapshot] = useState<MarketSnapshot | null>(null);
  const [marketSnapshotLoading, setMarketSnapshotLoading] = useState(false);
  const [input, setInput] = useState("");
  const [isHydrated, setIsHydrated] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const [showControlRail, setShowControlRail] = useState(false);
  const [showEntryAnimation, setShowEntryAnimation] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [error, setError] = useState("");
  const [threadMenuOpenId, setThreadMenuOpenId] = useState("");
  const [renamingThreadId, setRenamingThreadId] = useState("");
  const [renameValue, setRenameValue] = useState("");

  const messagesRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function syncViewport() {
      const desktop = window.innerWidth >= 1024;
      const controlRailVisible = window.innerWidth >= 1280;
      setIsDesktop(desktop);
      setShowControlRail(controlRailVisible);
      setSidebarOpen((current) => (desktop ? current : false));
    }

    syncViewport();
    window.addEventListener("resize", syncViewport);
    return () => window.removeEventListener("resize", syncViewport);
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setShowEntryAnimation(false);
    }, 1750);

    return () => window.clearTimeout(timeout);
  }, []);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);

      if (saved) {
        const parsed = JSON.parse(saved);
        const savedThreads = Array.isArray(parsed?.threads) ? parsed.threads : [];
        const savedMessages =
          parsed?.messagesByThread && typeof parsed.messagesByThread === "object"
            ? parsed.messagesByThread
            : {};
        const savedActive =
          typeof parsed?.activeThreadId === "string" ? parsed.activeThreadId : "";

        if (savedThreads.length > 0) {
          setThreads(savedThreads);
          setMessagesByThread(savedMessages);
          setActiveThreadId(savedActive || savedThreads[0].id);
        } else {
          const firstId = uid();
          setThreads([
            {
              id: firstId,
              title: "New thread",
              updatedAt: new Date().toISOString(),
            },
          ]);
          setMessagesByThread({
            [firstId]: [getInitialAssistantMessage()],
          });
          setActiveThreadId(firstId);
        }
      } else {
        const firstId = uid();
        setThreads([
          {
            id: firstId,
            title: "New thread",
            updatedAt: new Date().toISOString(),
          },
        ]);
        setMessagesByThread({
          [firstId]: [getInitialAssistantMessage()],
        });
        setActiveThreadId(firstId);
      }
    } catch {
      const firstId = uid();
      setThreads([
        {
          id: firstId,
          title: "New thread",
          updatedAt: new Date().toISOString(),
        },
      ]);
      setMessagesByThread({
        [firstId]: [getInitialAssistantMessage()],
      });
      setActiveThreadId(firstId);
    } finally {
      setIsHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!isHydrated) return;
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        threads,
        messagesByThread,
        activeThreadId,
      })
    );
  }, [threads, messagesByThread, activeThreadId, isHydrated]);

  useEffect(() => {
    if (!messagesRef.current) return;
    messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
  }, [activeThreadId, messagesByThread, isSending]);

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      const target = event.target;
      if (target instanceof HTMLElement && !target.closest("[data-thread-menu-shell]")) {
        setThreadMenuOpenId("");
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  const activeMessages = useMemo(() => {
    return messagesByThread[activeThreadId] || [];
  }, [messagesByThread, activeThreadId]);

  const latestAssistantMessage = useMemo(() => {
    for (let index = activeMessages.length - 1; index >= 0; index -= 1) {
      const message = activeMessages[index];
      if (message.role === "assistant") return message;
    }
    return null;
  }, [activeMessages]);

  useEffect(() => {
    if (!isHydrated || !activeThreadId) {
      setActiveSession(null);
      return;
    }

    const controller = new AbortController();
    const apiBaseUrl = getApiBaseUrl();

    if (!apiBaseUrl) {
      setActiveSession(null);
      return;
    }

    async function loadSession() {
      try {
        const response = await fetch(`${apiBaseUrl}/sessions/${activeThreadId}`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          if (response.status === 404) {
            setActiveSession(null);
            return;
          }
          throw new Error(`Session returned ${response.status}`);
        }

        const data = await response.json();
        if (!controller.signal.aborted) {
          setActiveSession(extractSessionDocument(data));
        }
      } catch {
        if (!controller.signal.aborted) {
          setActiveSession(null);
        }
      }
    }

    void loadSession();

    return () => controller.abort();
  }, [activeThreadId, isHydrated, activeMessages.length]);

  useEffect(() => {
    const needsMarketSnapshot = ["markets_tools", "portfolio_view"].includes(
      latestAssistantMessage?.visualHint || ""
    );

    if (!needsMarketSnapshot) {
      setMarketSnapshot(null);
      setMarketSnapshotLoading(false);
      return;
    }

    const controller = new AbortController();
    const apiBaseUrl = getApiBaseUrl();

    if (!apiBaseUrl) {
      setMarketSnapshot(null);
      setMarketSnapshotLoading(false);
      return;
    }

    async function loadMarketSnapshot() {
      setMarketSnapshotLoading(true);
      try {
        const response = await fetch(`${apiBaseUrl}/market-snapshot`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Market snapshot returned ${response.status}`);
        }

        const data = await response.json();
        if (!controller.signal.aborted) {
          setMarketSnapshot(extractMarketSnapshot(data));
        }
      } catch {
        if (!controller.signal.aborted) {
          setMarketSnapshot(null);
        }
      } finally {
        if (!controller.signal.aborted) {
          setMarketSnapshotLoading(false);
        }
      }
    }

    void loadMarketSnapshot();

    return () => controller.abort();
  }, [latestAssistantMessage?.visualHint]);

  function createNewThread() {
    const id = uid();
    const now = new Date().toISOString();

    setThreads((prev) => [
      {
        id,
        title: "New thread",
        updatedAt: now,
      },
      ...prev,
    ]);

    setMessagesByThread((prev) => ({
      ...prev,
      [id]: [getInitialAssistantMessage()],
    }));

    setActiveThreadId(id);
    setActiveSession(null);
    setMarketSnapshot(null);
    setInput("");
    setError("");
    setThreadMenuOpenId("");
    setRenamingThreadId("");
    setRenameValue("");
    return id;
  }

  function updateThreadMeta(threadId: string, title?: string) {
    const now = new Date().toISOString();

    setThreads((prev) => {
      const exists = prev.some((thread) => thread.id === threadId);

      if (!exists) {
        return [
          {
            id: threadId,
            title: title || "New thread",
            updatedAt: now,
          },
          ...prev,
        ];
      }

      const updated = prev.map((thread) =>
        thread.id === threadId
          ? {
              ...thread,
              title: title || thread.title,
              updatedAt: now,
            }
          : thread
      );

      return updated.sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
    });
  }

  function appendMessage(threadId: string, message: ChatMessage) {
    setMessagesByThread((prev) => ({
      ...prev,
      [threadId]: [...(prev[threadId] || []), message],
    }));
  }

  function selectThread(threadId: string) {
    setActiveThreadId(threadId);
    setThreadMenuOpenId("");
    setRenamingThreadId("");
    setRenameValue("");

    if (window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  }

  function startRenameThread(threadId: string) {
    const thread = threads.find((item) => item.id === threadId);
    if (!thread) return;

    setRenamingThreadId(threadId);
    setRenameValue(thread.title === "New thread" ? "" : thread.title);
    setThreadMenuOpenId("");
  }

  function saveRenameThread() {
    if (!renamingThreadId) return;

    updateThreadMeta(renamingThreadId, renameValue.trim() || "New thread");
    setRenamingThreadId("");
    setRenameValue("");
  }

  function deleteThread(threadId: string) {
    const remainingThreads = threads.filter((thread) => thread.id !== threadId);
    const nextMessages = { ...messagesByThread };
    delete nextMessages[threadId];

    if (remainingThreads.length === 0) {
      const nextId = uid();
      const now = new Date().toISOString();

      setThreads([
        {
          id: nextId,
          title: "New thread",
          updatedAt: now,
        },
      ]);
      setMessagesByThread({
        [nextId]: [getInitialAssistantMessage()],
      });
      setActiveThreadId(nextId);
      setActiveSession(null);
    } else {
      setThreads(remainingThreads);
      setMessagesByThread(nextMessages);

      if (activeThreadId === threadId) {
        setActiveThreadId(remainingThreads[0].id);
      }
    }

    if (renamingThreadId === threadId) {
      setRenamingThreadId("");
      setRenameValue("");
    }

    setThreadMenuOpenId("");
    setError("");
  }

  async function handleSend(queryOverride?: string) {
    const query = (queryOverride ?? input).trim();
    if (!query || isSending) return;

    setError("");

    let threadId = activeThreadId;
    if (!threadId) {
      threadId = createNewThread();
    }

    const currentThreadMessages = messagesByThread[threadId] || [];
    const shouldRenameThread =
      currentThreadMessages.length <= 1 ||
      threads.find((thread) => thread.id === threadId)?.title === "New thread";

    if (shouldRenameThread) {
      updateThreadMeta(threadId, makeThreadTitle(query));
    } else {
      updateThreadMeta(threadId);
    }

    const userMessage: ChatMessage = {
      id: uid(),
      role: "user",
      content: query,
      createdAt: new Date().toISOString(),
    };

    appendMessage(threadId, userMessage);
    setInput("");
    setIsSending(true);

    try {
      const apiBaseUrl = getApiBaseUrl();
      if (!apiBaseUrl) {
        throw new Error(getApiConfigurationError());
      }

      const minimumLoader = new Promise<void>((resolve) => {
        window.setTimeout(resolve, 1050);
      });

      const [response] = await Promise.all([
        fetch(`${apiBaseUrl}${API_CHAT_PATH}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query,
            thread_id: threadId,
          }),
        }),
        minimumLoader,
      ]);

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();

      const assistantMessage: ChatMessage = {
        id: uid(),
        role: "assistant",
        content: extractTextFromResponse(data),
        createdAt: new Date().toISOString(),
        sources: extractSources(data),
        sourceCitations: extractSourceCitations(data),
        recommendedProducts: extractStringArray(data.recommended_products),
        verificationNotes: extractStringArray(data.verification_notes),
        roadmap: extractRoadmap(data),
        chips: extractStringArray(data.chips),
        navigatorSummary: extractNavigatorSummary(data),
        visualHint: readString(data.visual_hint) || null,
        answerStyle: readString(data.answer_style),
        presentation: extractPresentation(data.presentation),
        decision: extractDecision(data),
        comparisonRows: extractComparisonRows(data),
        bulletGroups: extractBulletGroups(data),
        uiModules: extractUiModules(data),
        htmlSnippets: Array.isArray(data.html_snippets)
          ? data.html_snippets
              .map((item: unknown) => readString(item))
              .filter((item: string | undefined): item is string => Boolean(item))
          : [],
      };

      appendMessage(threadId, assistantMessage);
      updateThreadMeta(threadId);
    } catch (error: unknown) {
      const assistantErrorMessage: ChatMessage = {
        id: uid(),
        role: "assistant",
        content:
          "I couldn't reach the RAG server right now. Please verify your FastAPI server, endpoint path, and CORS settings.",
        createdAt: new Date().toISOString(),
      };

      appendMessage(threadId, assistantErrorMessage);
      setError(
        error instanceof Error
          ? error.message
          : "Something went wrong while contacting the server."
      );
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  const showEmptyState = activeMessages.every((message) => message.role !== "user");

  return (
    <div className="h-screen overflow-hidden bg-[#F0F0F0] text-[#121212]">
      <div
        className={`pointer-events-none fixed inset-0 z-[80] flex items-center justify-center bg-[#F0F0F0] px-4 transition-opacity duration-500 ${
          showEntryAnimation ? "opacity-100" : "opacity-0"
        }`}
        aria-hidden={!showEntryAnimation}
      >
        <div className="w-full max-w-3xl">
          <LunaThinkingPanel />
        </div>
      </div>

      <header className="fixed left-0 right-0 top-0 z-50 border-b-4 border-black bg-white">
        <div
          className="flex items-center px-3 sm:px-5 lg:px-6"
          style={{ height: `${SHELL_HEADER_H}px` }}
        >
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen((prev) => !prev)}
              className="inline-flex h-10 w-10 items-center justify-center border-2 border-black bg-white shadow-[4px_4px_0px_0px_black]"
            >
              {sidebarOpen ? <CloseIcon /> : <MenuIcon />}
            </button>

            <div className="min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-[#D02020] sm:text-[11px]">
                {etCompassContent.brand.name}
              </p>
              <h1 className="truncate font-black uppercase tracking-tight text-lg sm:text-xl lg:text-2xl">
                {etCompassContent.brand.assistantName}
              </h1>
            </div>
          </div>
        </div>
      </header>

      <div className="relative h-full" style={{ paddingTop: `${SHELL_HEADER_H}px` }}>
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-30 bg-black/25 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <ThreadRail
          activeThreadId={activeThreadId}
          headerHeight={SHELL_HEADER_H}
          renameValue={renameValue}
          renamingThreadId={renamingThreadId}
          sidebarOpen={sidebarOpen}
          sidebarWidth={THREAD_RAIL_W}
          threadMenuOpenId={threadMenuOpenId}
          threads={threads}
          onCreateThread={createNewThread}
          onDeleteThread={deleteThread}
          onRenameValueChange={setRenameValue}
          onSaveRenameThread={saveRenameThread}
          onSelectThread={selectThread}
          onStartRenameThread={startRenameThread}
          onToggleThreadMenu={(threadId) =>
            setThreadMenuOpenId((prev) => (prev === threadId ? "" : threadId))
          }
        />

        <ConciergeRail
          headerHeight={SHELL_HEADER_H}
          latestAssistantMessage={latestAssistantMessage}
          marketSnapshot={marketSnapshot}
          marketSnapshotLoading={marketSnapshotLoading}
          railWidth={CONTROL_RAIL_W}
          session={activeSession}
          visible={showControlRail}
          onQuickSend={(query) => {
            void handleSend(query);
          }}
        />

        <main
          className="transition-all duration-300"
          style={{
            height: `calc(100vh - ${SHELL_HEADER_H}px)`,
            marginLeft: sidebarOpen && isDesktop ? `${THREAD_RAIL_W}px` : "0px",
            marginRight: showControlRail ? `${CONTROL_RAIL_W}px` : "0px",
          }}
        >
          <div className="flex h-full flex-col">
            <div className="flex min-h-0 flex-1 flex-col bg-[#F0F0F0]">
              <div
                ref={messagesRef}
                className="flex-1 overflow-y-auto px-3 py-4 sm:px-5 sm:py-5"
              >
                <div className="mx-auto flex w-full max-w-5xl flex-col gap-3.5">
                  {showEmptyState ? (
                    <div className="border-4 border-black bg-white p-4 shadow-[8px_8px_0px_0px_black] sm:p-5">
                      <p className="mb-2 text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020] sm:text-[11px]">
                        {etCompassContent.searchPage.eyebrow}
                      </p>
                      <h3 className="mb-3 font-black uppercase text-2xl sm:text-3xl">
                        {etCompassContent.searchPage.emptyStateTitle}
                      </h3>
                      <p className="mb-4 max-w-3xl text-sm font-medium leading-relaxed opacity-80 sm:text-base">
                        {etCompassContent.searchPage.emptyStateDescription}
                      </p>

                      <div className="flex flex-wrap gap-2">
                        {etCompassContent.searchPage.quickPrompts.map((prompt) => (
                          <button
                            key={prompt}
                            type="button"
                            onClick={() => void handleSend(prompt)}
                            className="border-2 border-black bg-[#F0C020] px-3 py-2 text-left text-xs font-black uppercase tracking-[0.02em] shadow-[4px_4px_0px_0px_black] transition-transform hover:-translate-y-1"
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {activeMessages.map((message, index) => {
                    if (showEmptyState && index === 0 && message.role === "assistant") {
                      return null;
                    }

                    const isUser = message.role === "user";
                    const showRecommendedProducts =
                      message.presentation?.show_recommended_products ??
                      Boolean(message.recommendedProducts && message.recommendedProducts.length > 0);
                    const showNavigatorSummary =
                      message.presentation?.show_navigator_summary ??
                      Boolean(message.navigatorSummary);
                    const showVisualPanel =
                      message.presentation?.show_visual_panel ??
                      Boolean(message.visualHint);
                    const showRoadmap =
                      message.presentation?.show_roadmap ??
                      Boolean(message.roadmap && message.roadmap.steps && message.roadmap.steps.length > 0);
                    const showBulletGroups =
                      message.presentation?.show_bullet_groups ??
                      Boolean(message.bulletGroups && message.bulletGroups.length > 0);
                    const showComparisonTable =
                      message.presentation?.show_comparison_table ??
                      Boolean(message.comparisonRows && message.comparisonRows.length > 0);
                    const showChips =
                      message.presentation?.show_chips ??
                      Boolean(message.chips && message.chips.length > 0);
                    const nextActionModule = message.uiModules?.find(
                      (module) => module.module_type === "next_action" && module.visible !== false
                    );

                    return (
                      <div
                        key={message.id}
                        className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`max-w-[92%] border-2 border-black px-3 py-3 shadow-[4px_4px_0px_0px_black] sm:max-w-[78%] sm:px-4 ${
                            isUser ? "bg-white" : "bg-[#F0C020]"
                          }`}
                        >
                          <div className="mb-1.5 flex items-center justify-between gap-4">
                            <span
                              className={`text-[10px] font-black uppercase tracking-[0.18em] ${
                                isUser ? "text-[#1040C0]" : "text-[#D02020]"
                              }`}
                            >
                              {isUser ? "User" : etCompassContent.brand.shortTag}
                            </span>

                            <span className="text-[10px] font-bold uppercase tracking-wide text-black/45">
                              {formatTime(message.createdAt)}
                            </span>
                          </div>

                          <p className="whitespace-pre-wrap text-[13px] leading-6 sm:text-sm">
                            {message.content}
                          </p>

                          {!isUser && showBulletGroups && message.bulletGroups && message.bulletGroups.length > 0 ? (
                            <div className="mt-3 space-y-2">
                              {message.bulletGroups.map((group) => (
                                <div key={group.title} className="border-2 border-black bg-white p-3">
                                  <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#D02020]">
                                    {group.title}
                                  </p>
                                  <ul className="mt-2 space-y-1.5 text-[12px] font-medium leading-5 sm:text-[13px]">
                                    {group.items.map((item) => (
                                      <li key={item} className="flex gap-2">
                                        <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-black" />
                                        <span>{item}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              ))}
                            </div>
                          ) : null}

                          {!isUser && showComparisonTable && message.comparisonRows && message.comparisonRows.length > 0 ? (
                            <div className="mt-3 overflow-hidden border-2 border-black bg-white">
                              <div className="border-b-2 border-black bg-[#F7F7F7] px-3 py-2">
                                <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#D02020]">
                                  ET Comparison
                                </p>
                              </div>
                              <div className="overflow-x-auto">
                                <table className="min-w-full text-left">
                                  <thead>
                                    <tr className="border-b-2 border-black bg-[#FFF6CC]">
                                      <th className="px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em]">Product</th>
                                      <th className="px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em]">Best For</th>
                                      <th className="px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em]">Why</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {message.comparisonRows.map((row) => (
                                      <tr key={`${row.item}-${row.best_for}`} className="border-b border-black/20 align-top">
                                        <td className="px-3 py-2 text-[11px] font-black uppercase">{row.item}</td>
                                        <td className="px-3 py-2 text-[12px] font-medium">{row.best_for}</td>
                                        <td className="px-3 py-2 text-[12px] font-medium">{row.why}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          ) : null}

                          {!isUser && showRecommendedProducts && message.recommendedProducts && message.recommendedProducts.length > 0 ? (
                            <div className="mt-3 border-t-2 border-black/80 pt-2.5">
                              <p className="mb-2 text-[10px] font-black uppercase tracking-[0.18em] text-black/65">
                                Recommended Products
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {message.recommendedProducts.map((product) => (
                                  <span
                                    key={product}
                                    className="border border-black bg-[#1040C0] px-2.5 py-1 text-[10px] font-black uppercase tracking-wide text-white"
                                  >
                                    {product}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ) : null}

                          {!isUser && showNavigatorSummary && message.navigatorSummary ? (
                            <div className="mt-3 border-2 border-black bg-white p-3">
                              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#D02020]">
                                {message.navigatorSummary.title}
                              </p>
                              <p className="mt-2 text-[13px] font-medium leading-6 sm:text-sm">
                                {message.navigatorSummary.summary}
                              </p>

                              {message.navigatorSummary.why_this_path &&
                              message.navigatorSummary.why_this_path.length > 0 ? (
                                <div className="mt-3 space-y-1.5">
                                  {message.navigatorSummary.why_this_path.map((item) => (
                                    <p
                                      key={item}
                                      className="text-[11px] font-bold uppercase tracking-wide text-black/75"
                                    >
                                      {item}
                                    </p>
                                  ))}
                                </div>
                              ) : null}

                              {message.navigatorSummary.next_move ? (
                                <p className="mt-3 border-t-2 border-black pt-2 text-[11px] font-black uppercase tracking-wide text-[#1040C0]">
                                  Next Move: {message.navigatorSummary.next_move}
                                </p>
                              ) : null}
                            </div>
                          ) : null}

                          {!isUser && showVisualPanel ? (
                            <ResponseInsightPanel
                              visualHint={message.visualHint}
                              sourceCitations={message.sourceCitations}
                              recommendedProducts={message.recommendedProducts}
                              marketSnapshot={
                                message.id === latestAssistantMessage?.id ? marketSnapshot : null
                              }
                            />
                          ) : null}

                          {!isUser && message.verificationNotes && message.verificationNotes.length > 0 ? (
                            <div className="mt-3 border-2 border-black bg-[#FFD6D6] p-3">
                              <p className="mb-2 text-[10px] font-black uppercase tracking-[0.18em] text-[#D02020]">
                                Verification Notes
                              </p>
                              <div className="space-y-1.5">
                                {message.verificationNotes.map((note) => (
                                  <p key={note} className="text-[12px] font-bold leading-5 sm:text-[13px]">
                                    {note}
                                  </p>
                                ))}
                              </div>
                            </div>
                          ) : null}

                          {!isUser &&
                          nextActionModule &&
                          nextActionModule.payload &&
                          typeof nextActionModule.payload === "object" ? (
                            <div className="mt-3 border-2 border-black bg-[#DDE7FF] p-3 shadow-[3px_3px_0px_0px_black]">
                              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#1040C0]">
                                Next Best Action
                              </p>
                              <p className="mt-2 text-[12px] font-black uppercase leading-5 sm:text-[13px]">
                                {readString(nextActionModule.payload.label) || "Explore the next ET lane"}
                              </p>
                              {readString(nextActionModule.payload.reason) ? (
                                <p className="mt-2 text-[12px] font-medium leading-5 text-black/75 sm:text-[13px]">
                                  {readString(nextActionModule.payload.reason)}
                                </p>
                              ) : null}
                              {readString(nextActionModule.payload.href) ? (
                                <a
                                  href={readString(nextActionModule.payload.href)}
                                  className="mt-3 inline-flex items-center gap-2 border-2 border-black bg-white px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] shadow-[3px_3px_0px_0px_black]"
                                >
                                  Open next step
                                  <span aria-hidden="true">→</span>
                                </a>
                              ) : null}
                            </div>
                          ) : null}

                          {!isUser && showRoadmap && message.roadmap && message.roadmap.steps && message.roadmap.steps.length > 0 ? (
                            <div className="mt-3 border-2 border-black bg-white p-3">
                              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-[#D02020]">
                                {message.roadmap.title}
                              </p>

                              {message.roadmap.profile_summary && message.roadmap.profile_summary.length > 0 ? (
                                <div className="mt-2 flex flex-wrap gap-2">
                                  {message.roadmap.profile_summary.map((item) => (
                                    <span
                                      key={item}
                                      className="border border-black bg-[#F7F7F7] px-2 py-1 text-[10px] font-black uppercase tracking-wide"
                                    >
                                      {item.replaceAll("_", " ")}
                                    </span>
                                  ))}
                                </div>
                              ) : null}

                              <div className="mt-3 space-y-2">
                                {message.roadmap.steps.map((step) => (
                                  <div
                                    key={`${step.step}-${step.product}`}
                                    className="border-2 border-black bg-[#F7F7F7] p-2.5"
                                  >
                                    <div className="flex items-start gap-2">
                                      <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center border-2 border-black bg-[#F0C020] text-[10px] font-black">
                                        {step.step}
                                      </span>
                                      <div>
                                        <p className="text-[11px] font-black uppercase tracking-wide">
                                          {step.product}
                                        </p>
                                        <p className="mt-1 text-[12px] font-medium leading-5 sm:text-[13px]">
                                          {step.reason}
                                        </p>
                                        {step.url ? (
                                          <a
                                            href={step.url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="mt-2 inline-flex text-[10px] font-black uppercase tracking-[0.18em] text-[#1040C0]"
                                          >
                                            Open Product
                                          </a>
                                        ) : null}
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : null}

                          {!isUser && showChips && message.chips && message.chips.length > 0 ? (
                            <div className="mt-3 border-t-2 border-black/80 pt-2.5">
                              <p className="mb-2 text-[10px] font-black uppercase tracking-[0.18em] text-black/65">
                                Try Next
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {message.chips.map((chip) => (
                                  <button
                                    key={chip}
                                    type="button"
                                    onClick={() => void handleSend(chip)}
                                    className="border-2 border-black bg-white px-2.5 py-1.5 text-left text-[10px] font-black uppercase tracking-wide shadow-[3px_3px_0px_0px_black] transition-transform hover:-translate-y-0.5"
                                  >
                                    {chip}
                                  </button>
                                ))}
                              </div>
                            </div>
                          ) : null}

                          {!isUser && message.sources && message.sources.length > 0 ? (
                            <div className="mt-3 border-t-2 border-black/80 pt-2.5">
                              <p className="mb-2 text-[10px] font-black uppercase tracking-[0.18em] text-black/65">
                                Sources
                              </p>

                              <div className="flex flex-wrap gap-2">
                                {message.sources.map((source, idx) =>
                                  source.href ? (
                                    <a
                                      key={`${source.label}-${idx}`}
                                      href={source.href}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="border border-black bg-white px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide"
                                    >
                                      {source.label}
                                    </a>
                                  ) : (
                                    <span
                                      key={`${source.label}-${idx}`}
                                      className="border border-black bg-white px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide"
                                    >
                                      {source.label}
                                    </span>
                                  )
                                )}
                              </div>
                            </div>
                          ) : null}

                          {!isUser &&
                          message.sourceCitations &&
                          message.sourceCitations.length > 0 ? (
                            <div className="mt-3 border-t-2 border-black/80 pt-2.5">
                              <p className="mb-2 text-[10px] font-black uppercase tracking-[0.18em] text-black/65">
                                Verified Citations
                              </p>

                              <div className="space-y-2">
                                {message.sourceCitations.map((citation, idx) => {
                                  const content = (
                                    <>
                                      <span className="block text-[11px] font-black uppercase tracking-wide">
                                        {citation.label}
                                      </span>
                                      <span className="mt-1 block text-[10px] font-bold uppercase tracking-wide text-black/55">
                                        {[citation.pageType, citation.verificationStatus]
                                          .filter(Boolean)
                                          .join(" · ") || "ET source"}
                                      </span>
                                    </>
                                  );

                                  return citation.href ? (
                                    <a
                                      key={`${citation.label}-${idx}`}
                                      href={citation.href}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="block border border-black bg-white px-2.5 py-2"
                                    >
                                      {content}
                                    </a>
                                  ) : (
                                    <div
                                      key={`${citation.label}-${idx}`}
                                      className="border border-black bg-white px-2.5 py-2"
                                    >
                                      {content}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    );
                  })}

                  {isSending && (
                    <div className="flex justify-start">
                      <div className="max-w-[92%] sm:max-w-[78%]">
                        <LunaThinkingPanel />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="border-t-4 border-black bg-white px-3 py-2.5 sm:px-5">
                <div className="mx-auto w-full max-w-5xl">
                  {error ? (
                    <div className="mb-2.5 border-2 border-black bg-[#FFD6D6] px-3 py-2 text-xs font-bold">
                      {error}
                    </div>
                  ) : null}

                  <div className="border-2 border-black bg-[#F7F7F7] shadow-[4px_4px_0px_0px_black]">
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder={etCompassContent.searchPage.inputPlaceholder}
                      rows={2}
                      className="min-h-[72px] w-full resize-none bg-transparent px-3 py-3 text-[13px] outline-none sm:px-4 sm:text-sm"
                    />

                    <div className="flex flex-col gap-2.5 border-t-2 border-black bg-white p-2.5 sm:flex-row sm:items-center sm:justify-between">
                      <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-black/55">
                        Enter to send · Shift + Enter for new line
                      </p>

                      <button
                        type="button"
                        onClick={() => void handleSend()}
                        disabled={isSending || !input.trim()}
                        className="inline-flex items-center justify-center gap-2 border-2 border-black bg-[#D02020] px-4 py-2.5 text-xs font-black uppercase tracking-wide text-white shadow-[4px_4px_0px_0px_black] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <SendIcon />
                        {etCompassContent.searchPage.primaryButton}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
