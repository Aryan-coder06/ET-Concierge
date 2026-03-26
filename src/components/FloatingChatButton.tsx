"use client";

import Link from "next/link";

function LogoMark() {
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-4 w-4 rounded-full border border-black bg-[#D02020]" />
      <div className="h-4 w-4 border border-black bg-[#1040C0]" />
      <div
        className="h-4 w-4 border border-black bg-[#F0C020]"
        style={{ clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)" }}
      />
    </div>
  );
}

export default function FloatingChatButton() {
  return (
    <div className="pointer-events-none fixed inset-0 z-[70]">
      <div className="pointer-events-auto absolute bottom-4 right-4 sm:bottom-6 sm:right-6">
        <Link
          href="/search"
          className="group flex items-center gap-3 border-2 border-black bg-[#121212] px-4 py-3 text-white shadow-[6px_6px_0px_0px_#F0C020] transition-all hover:-translate-y-1 hover:shadow-[8px_8px_0px_0px_#F0C020]"
        >
          <LogoMark />
          <div className="leading-none">
            <div className="text-[11px] font-bold uppercase tracking-[0.22em] text-white/70">
              ET /
            </div>
            <div className="text-sm font-black uppercase tracking-wide">
              Open AI Concierge
            </div>
          </div>
        </Link>
      </div>
    </div>
  );
}