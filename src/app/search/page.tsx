"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

type Role = "user" | "assistant";

type SourceItem = {
  label: string;
  href?: string;
};

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  createdAt: string;
  sources?: SourceItem[];
};

type ThreadSummary = {
  id: string;
  title: string;
  updatedAt: string;
};

const STORAGE_KEY = "et-luna-chat-state";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const API_CHAT_PATH = "/chat";

const HEADER_H = 76;
const SIDEBAR_W = 320;

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
    content:
      "Hi, I’m Luna. Ask me anything and I’ll send your query to the ET RAG pipeline.",
    createdAt: new Date().toISOString(),
  };
}

function extractTextFromResponse(data: any): string {
  if (typeof data === "string") return data;

  const candidates = [
    data?.answer,
    data?.response,
    data?.message,
    data?.output,
    data?.text,
    data?.result,
    data?.data?.answer,
    data?.data?.response,
  ];

  for (const item of candidates) {
    if (typeof item === "string" && item.trim()) return item.trim();
  }

  return "Received a response from the server, but no readable answer field was found.";
}

function extractSources(data: any): SourceItem[] {
  const raw = data?.sources ?? data?.citations ?? data?.references ?? [];
  if (!Array.isArray(raw)) return [];

  return raw
    .map((item: any) => {
      if (typeof item === "string") return { label: item };
      if (item && typeof item === "object") {
        return {
          label:
            item.label ||
            item.title ||
            item.name ||
            item.source ||
            item.url ||
            "Source",
          href: item.href || item.url,
        };
      }
      return null;
    })
    .filter(Boolean) as SourceItem[];
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

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
      <path d="M3.4 20.4 21 12 3.4 3.6 3.3 10l12.2 2-12.2 2 .1 6.4Z" />
    </svg>
  );
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
      <path d="m12 2 1.7 5.3L19 9l-5.3 1.7L12 16l-1.7-5.3L5 9l5.3-1.7L12 2Z" />
      <path d="m19 14 .8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14Z" />
    </svg>
  );
}

export default function SearchPage() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [messagesByThread, setMessagesByThread] = useState<Record<string, ChatMessage[]>>({});
  const [activeThreadId, setActiveThreadId] = useState("");
  const [input, setInput] = useState("");
  const [isHydrated, setIsHydrated] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [error, setError] = useState("");

  const messagesRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
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

  function clearCurrentThread() {
    if (!activeThreadId) return;

    setMessagesByThread((prev) => ({
      ...prev,
      [activeThreadId]: [getInitialAssistantMessage()],
    }));

    setThreads((prev) =>
      prev.map((thread) =>
        thread.id === activeThreadId
          ? {
              ...thread,
              title: "New thread",
              updatedAt: new Date().toISOString(),
            }
          : thread
      )
    );

    setError("");
  }

  async function handleSend() {
    const query = input.trim();
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
      const response = await fetch(`${API_BASE_URL}${API_CHAT_PATH}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query,
          thread_id: threadId,
        }),
      });

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
      };

      appendMessage(threadId, assistantMessage);
      updateThreadMeta(threadId);
    } catch (err: any) {
      const assistantErrorMessage: ChatMessage = {
        id: uid(),
        role: "assistant",
        content:
          "I couldn’t reach the RAG server right now. Please verify your FastAPI server, endpoint path, and CORS settings.",
        createdAt: new Date().toISOString(),
      };

      appendMessage(threadId, assistantErrorMessage);
      setError(err?.message || "Something went wrong while contacting the server.");
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const activeTitle =
    threads.find((thread) => thread.id === activeThreadId)?.title || "New thread";

  return (
    <div className="h-screen overflow-hidden bg-[#F0F0F0] text-[#121212]">
      <header className="fixed left-0 right-0 top-0 z-50 border-b-4 border-black bg-white">
        <div className="flex h-[76px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen((prev) => !prev)}
              className="inline-flex h-11 w-11 items-center justify-center border-2 border-black bg-white shadow-[4px_4px_0px_0px_black]"
            >
              {sidebarOpen ? <CloseIcon /> : <MenuIcon />}
            </button>

            <div className="min-w-0">
              <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-[#D02020] sm:text-xs">
                ET /
              </p>
              <h1 className="truncate font-black uppercase tracking-tight text-xl sm:text-2xl lg:text-3xl">
                Luna AI Concierge
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={createNewThread}
              className="inline-flex items-center gap-2 border-2 border-black bg-[#D02020] px-3 py-2.5 text-sm font-black uppercase tracking-wide text-white shadow-[4px_4px_0px_0px_black] sm:px-4"
            >
              <PlusIcon />
              <span className="hidden sm:inline">New Chat</span>
            </button>

            <Link
              href="/"
              className="inline-flex items-center justify-center border-2 border-black bg-[#F0C020] px-3 py-2.5 text-sm font-black uppercase tracking-wide shadow-[4px_4px_0px_0px_black] sm:px-4"
            >
              Back Home
            </Link>
          </div>
        </div>
      </header>

      <div className="relative h-full pt-[76px]">
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-30 bg-black/25 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <aside
          className={`fixed top-[76px] z-40 h-[calc(100vh-76px)] border-r-4 border-black bg-white transition-all duration-300 ${
            sidebarOpen
              ? "left-0 w-[320px]"
              : "-left-[320px] w-[320px]"
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="border-b-4 border-black p-5">
              <h2 className="font-black uppercase text-2xl">Previous History</h2>
              <p className="mt-2 text-sm font-medium leading-relaxed text-black/65">
                Local thread list for now.
              </p>
            </div>

            <div className="border-b-4 border-black p-4">
              <button
                type="button"
                onClick={createNewThread}
                className="flex w-full items-center justify-center gap-2 border-2 border-black bg-[#1040C0] px-4 py-3 font-black uppercase tracking-wide text-white shadow-[4px_4px_0px_0px_black]"
              >
                <PlusIcon />
                Start New Thread
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              <div className="space-y-3">
                {threads.map((thread) => {
                  const isActive = thread.id === activeThreadId;

                  return (
                    <button
                      key={thread.id}
                      type="button"
                      onClick={() => {
                        setActiveThreadId(thread.id);
                        if (window.innerWidth < 1024) {
                          setSidebarOpen(false);
                        }
                      }}
                      className={`w-full border-2 border-black p-4 text-left shadow-[4px_4px_0px_0px_black] transition-all ${
                        isActive ? "bg-[#F0C020]" : "bg-white hover:bg-[#F7F7F7]"
                      }`}
                    >
                      <p className="truncate font-black uppercase text-sm">
                        {thread.title}
                      </p>
                      <p className="mt-2 text-[11px] font-bold uppercase tracking-wide text-black/55">
                        {formatDateLabel(thread.updatedAt)} · {formatTime(thread.updatedAt)}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </aside>

        <main
          className="h-[calc(100vh-76px)] transition-all duration-300"
          style={{
            marginLeft:
              sidebarOpen && typeof window !== "undefined" && window.innerWidth >= 1024
                ? `${SIDEBAR_W}px`
                : "0px",
          }}
        >
          <div className="flex h-full flex-col">
            <div className="border-b-4 border-black bg-white px-4 py-4 sm:px-6">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="min-w-0">
                  <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-[#D02020] sm:text-xs">
                    Active Thread
                  </p>
                  <h2 className="truncate font-black uppercase text-xl sm:text-2xl">
                    {activeTitle}
                  </h2>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <div className="inline-flex items-center gap-2 border-2 border-black bg-[#F7F7F7] px-3 py-2 text-[11px] font-black uppercase tracking-[0.22em]">
                    <SparkIcon />
                    RAG Connected
                  </div>

                  <button
                    type="button"
                    onClick={clearCurrentThread}
                    className="inline-flex items-center gap-2 border-2 border-black bg-white px-3 py-2 text-[11px] font-black uppercase tracking-[0.22em] shadow-[3px_3px_0px_0px_black]"
                  >
                    <TrashIcon />
                    Clear Thread
                  </button>
                </div>
              </div>
            </div>

            <div className="flex min-h-0 flex-1 flex-col bg-[#F0F0F0]">
              <div
                ref={messagesRef}
                className="flex-1 overflow-y-auto px-4 py-5 sm:px-6 sm:py-6"
              >
                <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
                  {activeMessages.map((message) => {
                    const isUser = message.role === "user";

                    return (
                      <div
                        key={message.id}
                        className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`max-w-[90%] border-2 border-black px-4 py-4 shadow-[4px_4px_0px_0px_black] sm:max-w-[78%] sm:px-5 ${
                            isUser ? "bg-white" : "bg-[#F0C020]"
                          }`}
                        >
                          <div className="mb-2 flex items-center justify-between gap-4">
                            <span
                              className={`text-xs font-black uppercase tracking-[0.24em] ${
                                isUser ? "text-[#1040C0]" : "text-[#D02020]"
                              }`}
                            >
                              {isUser ? "User" : "Luna"}
                            </span>

                            <span className="text-[11px] font-bold uppercase tracking-wide text-black/45">
                              {formatTime(message.createdAt)}
                            </span>
                          </div>

                          <p className="whitespace-pre-wrap text-sm leading-7 sm:text-base">
                            {message.content}
                          </p>

                          {!isUser && message.sources && message.sources.length > 0 ? (
                            <div className="mt-4 border-t-2 border-black/80 pt-3">
                              <p className="mb-2 text-[11px] font-black uppercase tracking-[0.24em] text-black/65">
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
                                      className="border border-black bg-white px-3 py-1 text-[11px] font-bold uppercase tracking-wide"
                                    >
                                      {source.label}
                                    </a>
                                  ) : (
                                    <span
                                      key={`${source.label}-${idx}`}
                                      className="border border-black bg-white px-3 py-1 text-[11px] font-bold uppercase tracking-wide"
                                    >
                                      {source.label}
                                    </span>
                                  )
                                )}
                              </div>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    );
                  })}

                  {isSending && (
                    <div className="flex justify-start">
                      <div className="max-w-[90%] border-2 border-black bg-[#F0C020] px-4 py-4 shadow-[4px_4px_0px_0px_black] sm:max-w-[78%] sm:px-5">
                        <div className="mb-2 flex items-center justify-between gap-4">
                          <span className="text-xs font-black uppercase tracking-[0.24em] text-[#D02020]">
                            Luna
                          </span>
                          <span className="text-[11px] font-bold uppercase tracking-wide text-black/45">
                            Thinking
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-black [animation-delay:-0.3s]" />
                          <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-black [animation-delay:-0.15s]" />
                          <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-black" />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="border-t-4 border-black bg-white px-4 py-4 sm:px-6">
                <div className="mx-auto w-full max-w-5xl">
                  {error ? (
                    <div className="mb-3 border-2 border-black bg-[#FFD6D6] px-4 py-3 text-sm font-bold">
                      {error}
                    </div>
                  ) : null}

                  <div className="mb-3 flex flex-wrap gap-2">
                    <span className="border border-black bg-[#F7F7F7] px-3 py-1 text-[11px] font-bold uppercase tracking-wide">
                      POST {API_CHAT_PATH}
                    </span>
                    <span className="border border-black bg-[#F7F7F7] px-3 py-1 text-[11px] font-bold uppercase tracking-wide">
                      FastAPI
                    </span>
                    <span className="border border-black bg-[#F7F7F7] px-3 py-1 text-[11px] font-bold uppercase tracking-wide">
                      Thread Aware
                    </span>
                  </div>

                  <div className="border-2 border-black bg-[#F7F7F7] shadow-[4px_4px_0px_0px_black]">
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Ask Luna anything… policy, markets, power sector updates, ET knowledge retrieval, and more."
                      rows={3}
                      className="min-h-[96px] w-full resize-none bg-transparent px-4 py-4 text-sm outline-none sm:px-5 sm:text-base"
                    />

                    <div className="flex flex-col gap-3 border-t-2 border-black bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
                      <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-black/55">
                        Enter to send · Shift + Enter for new line
                      </p>

                      <button
                        type="button"
                        onClick={handleSend}
                        disabled={isSending || !input.trim()}
                        className="inline-flex items-center justify-center gap-2 border-2 border-black bg-[#D02020] px-5 py-3 text-sm font-black uppercase tracking-wide text-white shadow-[4px_4px_0px_0px_black] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <SendIcon />
                        Send to Luna
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