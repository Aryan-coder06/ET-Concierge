"use client";

import Link from "next/link";
import type { ThreadSummary } from "@/components/search/types";

type Props = {
  activeThreadId: string;
  headerHeight: number;
  renameValue: string;
  renamingThreadId: string;
  sidebarOpen: boolean;
  sidebarWidth: number;
  threadMenuOpenId: string;
  threads: ThreadSummary[];
  onCreateThread: () => void;
  onDeleteThread: (threadId: string) => void;
  onRenameValueChange: (value: string) => void;
  onSaveRenameThread: () => void;
  onSelectThread: (threadId: string) => void;
  onStartRenameThread: (threadId: string) => void;
  onToggleThreadMenu: (threadId: string) => void;
};

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

export function ThreadRail({
  activeThreadId,
  headerHeight,
  renameValue,
  renamingThreadId,
  sidebarOpen,
  sidebarWidth,
  threadMenuOpenId,
  threads,
  onCreateThread,
  onDeleteThread,
  onRenameValueChange,
  onSaveRenameThread,
  onSelectThread,
  onStartRenameThread,
  onToggleThreadMenu,
}: Props) {
  return (
    <aside
      className="fixed z-40 border-r-4 border-black bg-white transition-all duration-300"
      style={{
        left: sidebarOpen ? "0px" : `-${sidebarWidth}px`,
        top: `${headerHeight}px`,
        height: `calc(100vh - ${headerHeight}px)`,
        width: `${sidebarWidth}px`,
      }}
    >
      <div className="flex h-full flex-col overflow-hidden">
        <div className="border-b-4 border-black p-4">
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020]">
            Thread Rail
          </p>
          <h2 className="mt-1 font-black uppercase text-lg">Your Threads</h2>
        </div>

        <div className="border-b-4 border-black p-3">
          <button
            type="button"
            onClick={onCreateThread}
            className="flex w-full items-center justify-center gap-2 border-2 border-black bg-[#1040C0] px-3 py-2.5 text-xs font-black uppercase tracking-wide text-white shadow-[4px_4px_0px_0px_black]"
          >
            <PlusIcon />
            Start New Thread
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
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
                        onChange={(event) => onRenameValueChange(event.target.value)}
                        onBlur={onSaveRenameThread}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.preventDefault();
                            onSaveRenameThread();
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
                      onClick={() => onSelectThread(thread.id)}
                      className="w-full text-left"
                    >
                      <p className="truncate font-black uppercase text-xs">{thread.title}</p>
                      <p className="mt-1.5 text-[10px] font-bold uppercase tracking-wide text-black/55">
                        {formatDateLabel(thread.updatedAt)} · {formatTime(thread.updatedAt)}
                      </p>
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onToggleThreadMenu(thread.id);
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
                        onClick={() => onStartRenameThread(thread.id)}
                        className="inline-flex items-center gap-2 border-b-2 border-black px-3 py-2 text-xs font-black uppercase tracking-wide hover:bg-[#F7F7F7]"
                      >
                        <EditIcon />
                        Rename
                      </button>
                      <button
                        type="button"
                        onClick={() => onDeleteThread(thread.id)}
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
            Back to ET Compass
          </Link>
        </div>
      </div>
    </aside>
  );
}
