"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { LunaThinkingPanel } from "@/components/search/LunaThinkingPanel";
import { ResponseInsightPanel } from "@/components/search/ResponseInsightPanel";
import { etCompassContent } from "@/content/etCompassContent";

type Role = "user" | "assistant";

type SourceItem = {
  label: string;
  href?: string;
};

type SourceCitation = {
  label: string;
  href?: string;
  sourceId?: string;
  verificationStatus?: string;
  pageType?: string;
};

type RoadmapStep = {
  step: number;
  product: string;
  reason: string;
  url?: string;
};

type Roadmap = {
  title: string;
  profile_summary?: string[];
  steps?: RoadmapStep[];
};

type NavigatorSummary = {
  title: string;
  summary: string;
  why_this_path?: string[];
  next_move?: string;
};

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  createdAt: string;
  sources?: SourceItem[];
  sourceCitations?: SourceCitation[];
  recommendedProducts?: string[];
  verificationNotes?: string[];
  roadmap?: Roadmap;
  chips?: string[];
  navigatorSummary?: NavigatorSummary | null;
  visualHint?: string | null;
};

type ThreadSummary = {
  id: string;
  title: string;
  updatedAt: string;
};

type JsonRecord = Record<string, unknown>;

const STORAGE_KEY = "et-compass-luna-chat-state";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const API_CHAT_PATH = "/chat";

const SHELL_HEADER_H = 68;
const SIDEBAR_W = 300;

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

function formatDateLabel(value: string) {
  try {
    return new Date(value).toLocaleDateString([], {
      day: "2-digit",
      month: "short",
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

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </svg>
  );
}

function DotsIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
      <circle cx="5" cy="12" r="1.8" />
      <circle cx="12" cy="12" r="1.8" />
      <circle cx="19" cy="12" r="1.8" />
    </svg>
  );
}

function EditIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 20h4l10-10-4-4L4 16v4Z" />
      <path d="m12 6 4 4" />
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
  const [input, setInput] = useState("");
  const [isHydrated, setIsHydrated] = useState(false);
  const [showEntryAnimation, setShowEntryAnimation] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [error, setError] = useState("");
  const [threadMenuOpenId, setThreadMenuOpenId] = useState("");
  const [renamingThreadId, setRenamingThreadId] = useState("");
  const [renameValue, setRenameValue] = useState("");

  const messagesRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
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
      const minimumLoader = new Promise<void>((resolve) => {
        window.setTimeout(resolve, 1050);
      });

      const [response] = await Promise.all([
        fetch(`${API_BASE_URL}${API_CHAT_PATH}`, {
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

        <aside
          className={`fixed z-40 border-r-4 border-black bg-white transition-all duration-300 ${
            sidebarOpen
              ? "left-0 w-[300px]"
              : "-left-[300px] w-[300px]"
          }`}
          style={{
            top: `${SHELL_HEADER_H}px`,
            height: `calc(100vh - ${SHELL_HEADER_H}px)`,
          }}
        >
          <div className="flex h-full flex-col">
            <div className="border-b-4 border-black p-4">
              <h2 className="font-black uppercase text-xl">Previous History</h2>
              <p className="mt-1.5 text-xs font-medium leading-relaxed text-black/65">
                Local thread list for now.
              </p>
            </div>

            <div className="border-b-4 border-black p-3">
              <button
                type="button"
                onClick={createNewThread}
                className="flex w-full items-center justify-center gap-2 border-2 border-black bg-[#1040C0] px-3 py-2.5 text-xs font-black uppercase tracking-wide text-white shadow-[4px_4px_0px_0px_black]"
              >
                <PlusIcon />
                Start New Thread
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-3">
              <div className="space-y-2.5">
                {threads.map((thread) => {
                  const isActive = thread.id === activeThreadId;
                  const isRenaming = renamingThreadId === thread.id;

                  return (
                    <div
                      key={thread.id}
                      data-thread-menu-shell
                      className={`relative border-2 border-black p-3 pr-12 shadow-[4px_4px_0px_0px_black] transition-all ${
                        isActive ? "bg-[#F0C020]" : "bg-white hover:bg-[#F7F7F7]"
                      }`}
                    >
                      {isRenaming ? (
                        <div>
                          <input
                            value={renameValue}
                            onChange={(e) => setRenameValue(e.target.value)}
                            onBlur={saveRenameThread}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                e.preventDefault();
                                saveRenameThread();
                              }

                              if (e.key === "Escape") {
                                setRenamingThreadId("");
                                setRenameValue("");
                              }
                            }}
                            autoFocus
                            className="w-full border-2 border-black bg-white px-2 py-1.5 text-xs font-black uppercase outline-none"
                          />
                          <p className="mt-1.5 text-[10px] font-bold uppercase tracking-wide text-black/55">
                            Press enter to save
                          </p>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => selectThread(thread.id)}
                          className="w-full text-left"
                        >
                          <p className="truncate font-black uppercase text-xs">
                            {thread.title}
                          </p>
                          <p className="mt-1.5 text-[10px] font-bold uppercase tracking-wide text-black/55">
                            {formatDateLabel(thread.updatedAt)} · {formatTime(thread.updatedAt)}
                          </p>
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setThreadMenuOpenId((prev) => (prev === thread.id ? "" : thread.id));
                        }}
                        className="absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center border-2 border-black bg-white shadow-[2px_2px_0px_0px_black]"
                        aria-label={`Open menu for ${thread.title}`}
                      >
                        <DotsIcon />
                      </button>

                      {threadMenuOpenId === thread.id ? (
                        <div className="absolute right-2 top-12 z-10 flex min-w-[132px] flex-col border-2 border-black bg-white shadow-[4px_4px_0px_0px_black]">
                          <button
                            type="button"
                            onClick={() => startRenameThread(thread.id)}
                            className="inline-flex items-center gap-2 border-b-2 border-black px-3 py-2 text-xs font-black uppercase tracking-wide hover:bg-[#F7F7F7]"
                          >
                            <EditIcon />
                            Rename
                          </button>
                          <button
                            type="button"
                            onClick={() => deleteThread(thread.id)}
                            className="inline-flex items-center gap-2 px-3 py-2 text-xs font-black uppercase tracking-wide text-[#D02020] hover:bg-[#FFF0F0]"
                          >
                            <TrashIcon />
                            Delete
                          </button>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
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

        <main
          className="transition-all duration-300"
          style={{
            height: `calc(100vh - ${SHELL_HEADER_H}px)`,
            marginLeft:
              sidebarOpen && typeof window !== "undefined" && window.innerWidth >= 1024
                ? `${SIDEBAR_W}px`
                : "0px",
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

                          {!isUser && message.recommendedProducts && message.recommendedProducts.length > 0 ? (
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

                          {!isUser && message.navigatorSummary ? (
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

                          {!isUser ? (
                            <ResponseInsightPanel
                              visualHint={message.visualHint}
                              sourceCitations={message.sourceCitations}
                              recommendedProducts={message.recommendedProducts}
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

                          {!isUser && message.roadmap && message.roadmap.steps && message.roadmap.steps.length > 0 ? (
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

                          {!isUser && message.chips && message.chips.length > 0 ? (
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
