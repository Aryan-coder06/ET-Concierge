'use client';

import { useEffect, useRef } from "react";
import { animate, stagger, svg } from "animejs";

export function LunaThinkingPanel() {
  const windowRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const fillRef = useRef<SVGTextElement | null>(null);
  const statusRef = useRef<HTMLParagraphElement | null>(null);

  useEffect(() => {
    if (!windowRef.current || !svgRef.current || !fillRef.current || !statusRef.current) {
      return;
    }

    const lines = Array.from(
      svgRef.current.querySelectorAll<
        SVGPathElement | SVGPolylineElement | SVGLineElement | SVGRectElement
      >(".luna-draw-line")
    );
    const drawables = lines.flatMap((line) => svg.createDrawable(line));

    const slideAnimation = animate(windowRef.current, {
      translateY: ["108%", "0%"],
      duration: 900,
      ease: "inOutQuad",
    });

    const drawAnimation = animate(drawables, {
      draw: ["0 0", "0 1", "1 1"],
      ease: "inOutQuad",
      duration: 1900,
      delay: stagger(110),
      loop: true,
    });

    const fillAnimation = animate(fillRef.current, {
      opacity: [0.16, 0.92, 0.22],
      duration: 1800,
      ease: "inOutQuad",
      loop: true,
    });

    const statusAnimation = animate(statusRef.current, {
      opacity: [0.45, 1, 0.45],
      duration: 1500,
      ease: "inOutQuad",
      loop: true,
    });

    return () => {
      slideAnimation.cancel();
      drawAnimation.cancel();
      fillAnimation.cancel();
      statusAnimation.cancel();
    };
  }, []);

  return (
    <div className="w-full overflow-hidden border-2 border-black bg-[#FFE4E4] shadow-[4px_4px_0px_0px_black]">
      <div className="relative min-h-[224px]">
        <div
          ref={windowRef}
          className="absolute inset-x-0 bottom-0 h-[70%] border-t-2 border-black bg-[#D02020]"
          style={{ transform: "translateY(108%)" }}
        />

        <div className="relative z-10 flex min-h-[224px] flex-col justify-between gap-4 p-4 sm:p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[#D02020]">
                LUNA Thinking
              </p>
              <p className="mt-1 text-[11px] font-bold uppercase tracking-[0.18em] text-black/65">
                Mapping ET signals into the next best path
              </p>
            </div>
            <span className="border border-black bg-white px-2 py-1 text-[9px] font-black uppercase tracking-[0.22em]">
              Live Retrieval
            </span>
          </div>

          <div className="relative overflow-hidden border-2 border-black bg-[#F6B4B4] px-3 py-4 sm:px-4">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.26),transparent_58%)]" />
            <svg
              ref={svgRef}
              viewBox="0 0 320 112"
              className="relative z-10 w-full text-white"
              fill="none"
            >
              <text
                ref={fillRef}
                x="16"
                y="83"
                fill="currentColor"
                fontFamily="var(--font-outfit), ui-sans-serif, system-ui, sans-serif"
                fontSize="72"
                fontWeight="900"
                letterSpacing="7"
                opacity="0.16"
              >
                LUNA
              </text>

              <g
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="7"
              >
                <path className="luna-draw-line" d="M24 18V78H72" />
                <path className="luna-draw-line" d="M102 18V58C102 70 111 78 124 78C137 78 146 70 146 58V18" />
                <polyline className="luna-draw-line" points="172 78 172 18 220 78 220 18" />
                <polyline className="luna-draw-line" points="246 78 270 18 294 78" />
                <line className="luna-draw-line" x1="254" y1="56" x2="286" y2="56" />
              </g>
            </svg>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-white shadow-[0_0_0_2px_black]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#F0C020] shadow-[0_0_0_2px_black]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#1040C0] shadow-[0_0_0_2px_black]" />
            </div>

            <p
              ref={statusRef}
              className="text-[10px] font-black uppercase tracking-[0.24em] text-white"
            >
              Reading ET context and shaping the answer
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
