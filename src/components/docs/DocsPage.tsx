import Image from "next/image";
import Link from "next/link";

const btnBase =
  "inline-flex items-center justify-center border-2 border-black font-bold uppercase tracking-wider transition-all active:translate-x-[2px] active:translate-y-[2px] active:shadow-none";
const btnPrimary =
  `${btnBase} bg-[#D02020] text-white shadow-[4px_4px_0px_0px_#121212] hover:bg-[#ba1b1b]`;
const btnSecondary =
  `${btnBase} bg-white text-[#121212] shadow-[4px_4px_0px_0px_#121212] hover:bg-[#F0F0F0]`;

const contributors = [
  {
    name: "Aryan",
    handle: "@Aryan-coder06",
    href: "https://github.com/Aryan-coder06",
    accent: "bg-[#D02020]",
    role: "Platform, responsive frontend, connected backend flow, and RAG amplification",
    summary:
      "Built the complete ET Compass platform, reimplemented the responsive UI infrastructure, connected the backend graph end-to-end, and strengthened the RAG presentation layer so answers, widgets, and navigation work together.",
    focus: [
      "Complete platform architecture and responsive frontend",
      "Backend node wiring, API integration, and production-ready flow",
      "Internal RAG upgrades around response planning, answer shaping, and UI sync",
    ],
  },
  {
    name: "Ajay",
    handle: "@ajaykathar30",
    href: "https://github.com/ajaykathar30",
    accent: "bg-[#1040C0]",
    role: "RAG foundation, MongoDB session memory, and hybrid ET retrieval",
    summary:
      "Built the original RAG path from scratch, set up MongoDB-backed session memory, created the dedicated retrieval pipeline, and established the hybrid-search foundation that keeps Luna grounded in ET knowledge.",
    focus: [
      "RAG from scratch with clear ET retrieval pathways",
      "MongoDB session persistence and conversation memory",
      "Hybrid search and ET-grounded knowledge flow",
    ],
  },
] as const;

const architectureSteps = [
  {
    step: "01",
    title: "Intent Capture",
    description:
      "Luna reads the user's natural question and identifies whether the need is discovery, markets, learning, events, benefits, roadmap, or comparison.",
  },
  {
    step: "02",
    title: "Profile Memory",
    description:
      "The system uses session memory to retain profile signals like user type, goal, experience level, and ET lane without forcing the user to repeat everything.",
  },
  {
    step: "03",
    title: "Hybrid Retrieval",
    description:
      "ET product registry, curated ET sources, vector retrieval, and keyword matching are combined so the answer stays grounded and not purely generative.",
  },
  {
    step: "04",
    title: "Product Scoring",
    description:
      "Each question is scored against ET lanes like ET Prime, ET Markets, ET Portfolio, ET Masterclass, ET Events, and ET Benefits to find the best fit.",
  },
  {
    step: "05",
    title: "Response Planner",
    description:
      "A unified decision object chooses answer depth, structure, next action, and whether the UI should help with bullets, tables, or a contextual module.",
  },
  {
    step: "06",
    title: "Answer and UI Sync",
    description:
      "The final response and the frontend use the same decision state, so Luna's text, widgets, and concierge rail stay aligned.",
  },
] as const;

const ragConcepts = [
  "Hybrid Retrieval",
  "MongoDB Session Memory",
  "Response Planner",
  "Unified Decision Object",
  "Product Scoring",
  "Answer/UI Sync",
  "Format-Aware Rendering",
] as const;

const productHighlights = [
  {
    title: "Natural ET Concierge Chat",
    description:
      "Luna answers open ET questions in a more human way instead of behaving like a rigid form or static FAQ.",
  },
  {
    title: "Profile-Aware Guidance",
    description:
      "The system remembers the user's path and keeps narrowing to the right ET lane over time.",
  },
  {
    title: "Hybrid ET Knowledge Retrieval",
    description:
      "ET registry data, curated ET sources, keyword cues, and vector retrieval work together to keep responses grounded.",
  },
  {
    title: "Structured Recommendations",
    description:
      "Luna does not just answer. It scores ET products, chooses a primary path, and proposes the next best action.",
  },
  {
    title: "Contextual UI Blocks",
    description:
      "The frontend can show tables, bullets, next actions, and market context only when those formats actually help.",
  },
  {
    title: "Responsive Full Platform",
    description:
      "The project includes the landing page, auth flows, profile dashboard, concierge search UI, and deployable backend/frontend split.",
  },
  {
    title: "Hackathon-Ready Architecture",
    description:
      "The stack is documented, measurable, and built to evolve into voice, deeper profiling, and stronger ET service guidance.",
  },
] as const;

function LogoMark() {
  return (
    <div className="flex items-center gap-1.5 sm:gap-2">
      <div className="h-6 w-6 rounded-full border-2 border-black bg-[#D02020] sm:h-8 sm:w-8" />
      <div className="h-6 w-6 border-2 border-black bg-[#1040C0] sm:h-8 sm:w-8" />
      <div
        className="h-6 w-6 border-2 border-black bg-[#F0C020] sm:h-8 sm:w-8"
        style={{ clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)" }}
      />
    </div>
  );
}

function GitHubIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 .5C5.65.5.5 5.8.5 12.33c0 5.23 3.3 9.67 7.88 11.24.58.11.79-.26.79-.58 0-.28-.01-1.22-.02-2.22-3.2.71-3.88-1.4-3.88-1.4-.52-1.37-1.28-1.73-1.28-1.73-1.05-.73.08-.72.08-.72 1.16.08 1.77 1.23 1.77 1.23 1.03 1.82 2.7 1.3 3.36.99.1-.77.4-1.3.72-1.6-2.55-.3-5.23-1.32-5.23-5.87 0-1.3.45-2.36 1.2-3.2-.12-.3-.52-1.5.12-3.12 0 0 .98-.32 3.2 1.22a10.83 10.83 0 0 1 5.84 0c2.22-1.54 3.2-1.22 3.2-1.22.64 1.62.24 2.82.12 3.12.75.84 1.2 1.9 1.2 3.2 0 4.56-2.68 5.57-5.24 5.87.41.36.78 1.07.78 2.17 0 1.56-.01 2.82-.01 3.2 0 .31.21.69.8.57 4.57-1.57 7.86-6.01 7.86-11.24C23.5 5.8 18.35.5 12 .5Z" />
    </svg>
  );
}

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-[#F0F0F0] text-[#121212] selection:bg-[#F0C020] selection:text-black">
      <nav className="sticky top-0 z-40 border-b-4 border-black bg-white">
        <div className="mx-auto flex h-[78px] max-w-[1400px] items-center gap-4 px-4 sm:px-6 xl:px-8">
          <Link href="/" className="flex shrink-0 items-center gap-3">
            <LogoMark />
            <div className="leading-none">
              <span className="block text-[11px] font-black uppercase tracking-[0.28em] text-[#D02020] sm:text-xs">
                ET
              </span>
              <span className="block pt-0.5 font-black uppercase tracking-tight text-xl sm:text-[1.9rem]">
                COMPASS
              </span>
            </div>
          </Link>

          <div className="ml-auto flex items-center gap-3">
            <Link href="/search" className={`${btnSecondary} h-12 rounded-full px-5 text-sm`}>
              Open Luna
            </Link>
            <Link
              href="https://github.com/Aryan-coder06/ET-Concierge"
              target="_blank"
              rel="noreferrer"
              className={`${btnPrimary} h-12 gap-2 rounded-full px-5 text-sm`}
            >
              <GitHubIcon className="h-4 w-4" />
              GitHub
            </Link>
          </div>
        </div>
      </nav>

      <main>
        <section className="border-b-4 border-black bg-white">
          <div className="mx-auto grid max-w-[1400px] gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:px-8 lg:py-14">
            <div className="flex flex-col justify-center">
              <p className="mb-4 text-sm font-black uppercase tracking-[0.3em] text-[#D02020]">
                Luna for ET / Documentation
              </p>
              <h1 className="max-w-[10ch] font-black uppercase leading-[0.9] tracking-[-0.05em] text-[3rem] sm:text-[4rem] lg:text-[5rem]">
                How Luna Was Built for the ET Concierge.
              </h1>
              <p className="mt-6 max-w-2xl border-l-8 border-[#D02020] pl-5 text-lg leading-relaxed sm:text-xl">
                This page explains, in a user-friendly way, how{" "}
                <span className="font-black uppercase">Aryan</span> and{" "}
                <span className="font-black uppercase">Ajay</span> built ET
                Compass: the product flow, the RAG engine, the memory layer,
                and the planning logic that makes Luna feel like a real ET
                guide instead of a plain chatbot.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                {ragConcepts.map((concept, index) => (
                  <span
                    key={concept}
                    className={`border-2 border-black px-3 py-2 text-xs font-black uppercase tracking-[0.18em] underline decoration-[3px] underline-offset-[6px] ${index % 3 === 0 ? "bg-[#FFF3B8]" : index % 3 === 1 ? "bg-[#E6EEFF]" : "bg-[#FFE4E4]"}`}
                  >
                    {concept}
                  </span>
                ))}
              </div>
            </div>

            <div className="relative overflow-hidden border-4 border-black bg-[#121212] shadow-[8px_8px_0px_0px_black]">
              <Image
                src="/MD_HEADER.png"
                alt="ET Compass technical documentation header"
                width={1600}
                height={900}
                className="h-full w-full object-cover"
                priority
              />
              <div className="absolute inset-0 bg-black/25" />
              <div className="absolute bottom-5 left-5 right-5 border-2 border-black bg-white/90 p-4 shadow-[5px_5px_0px_0px_black]">
                <p className="text-[11px] font-black uppercase tracking-[0.24em] text-[#D02020]">
                  Build Focus
                </p>
                <p className="mt-2 text-sm font-medium leading-relaxed sm:text-base">
                  ET-first concierge guidance, hybrid retrieval, persistent
                  session memory, structured response planning, and responsive
                  product UX in one platform.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="border-b-4 border-black bg-[#F0F0F0] py-16 sm:py-20">
          <div className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-8">
            <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-sm font-black uppercase tracking-[0.28em] text-[#D02020]">
                  Core Team
                </p>
                <h2 className="mt-3 font-black uppercase leading-none tracking-tight text-4xl sm:text-5xl">
                  Who Built What
                </h2>
              </div>
              <p className="max-w-2xl text-base font-medium leading-relaxed sm:text-lg">
                The platform was built as a collaboration between product,
                frontend, backend orchestration, and RAG engineering. The roles
                below keep the story clean and technically honest.
              </p>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              {contributors.map((contributor) => (
                <article
                  key={contributor.handle}
                  className="border-4 border-black bg-white p-6 shadow-[8px_8px_0px_0px_black]"
                >
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-black uppercase tracking-[0.3em] text-[#D02020]">
                        Contributor
                      </p>
                      <h3 className="mt-3 font-black uppercase tracking-tight text-3xl">
                        {contributor.name}
                      </h3>
                      <Link
                        href={contributor.href}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2 inline-flex text-sm font-black uppercase tracking-[0.16em] text-[#1040C0] underline underline-offset-4"
                      >
                        {contributor.handle}
                      </Link>
                    </div>
                    <div className={`h-12 w-12 border-2 border-black ${contributor.accent}`} />
                  </div>

                  <p className="mt-5 text-lg font-bold leading-relaxed">
                    {contributor.role}
                  </p>
                  <p className="mt-4 text-base leading-relaxed text-[#333]">
                    {contributor.summary}
                  </p>

                  <div className="mt-6 grid gap-3">
                    {contributor.focus.map((item) => (
                      <div
                        key={item}
                        className="border-2 border-black bg-[#F8F8F8] px-4 py-3 text-sm font-medium leading-relaxed"
                      >
                        {item}
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b-4 border-black bg-[#1040C0] py-16 text-white sm:py-20">
          <div className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl">
              <p className="text-sm font-black uppercase tracking-[0.28em] text-[#F0C020]">
                Architecture
              </p>
              <h2 className="mt-3 font-black uppercase leading-[0.92] tracking-tight text-4xl sm:text-5xl lg:text-6xl">
                The ET Concierge RAG Flow
              </h2>
            </div>

            <div className="mt-10 grid gap-5 lg:grid-cols-3">
              {architectureSteps.map((step) => (
                <article
                  key={step.step}
                  className="border-4 border-black bg-white p-6 text-[#121212] shadow-[8px_8px_0px_0px_black]"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-black uppercase tracking-[0.3em] text-[#D02020]">
                      {step.step}
                    </span>
                    <div className="h-8 w-8 rounded-full border-2 border-black bg-[#F0C020]" />
                  </div>
                  <h3 className="mt-4 font-black uppercase tracking-tight text-2xl">
                    {step.title}
                  </h3>
                  <p className="mt-4 text-base leading-relaxed text-[#333]">
                    {step.description}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b-4 border-black bg-white py-16 sm:py-20">
          <div className="mx-auto grid max-w-[1400px] gap-8 px-4 sm:px-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:px-8">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.28em] text-[#D02020]">
                Why This RAG Is Stronger
              </p>
              <h2 className="mt-3 font-black uppercase leading-[0.92] tracking-tight text-4xl sm:text-5xl">
                Smarter Than a Simple Chat Wrapper
              </h2>
            </div>
            <div className="space-y-5 text-base leading-relaxed text-[#262626] sm:text-lg">
              <p>
                Luna is not only retrieving chunks and sending them to a model.
                The system combines{" "}
                <span className="font-black underline decoration-[#F0C020] decoration-[3px] underline-offset-4">
                  hybrid retrieval
                </span>
                ,{" "}
                <span className="font-black underline decoration-[#D02020] decoration-[3px] underline-offset-4">
                  session memory
                </span>
                ,{" "}
                <span className="font-black underline decoration-[#1040C0] decoration-[3px] underline-offset-4">
                  product scoring
                </span>
                , and a{" "}
                <span className="font-black underline decoration-[#F0C020] decoration-[3px] underline-offset-4">
                  response planner
                </span>{" "}
                so the answer feels intentional.
              </p>
              <p>
                That means the backend decides not only the text, but also the
                best ET lane, the next step, and whether the interface should
                render a cleaner table, bullet structure, or contextual module.
                This is the core of{" "}
                <span className="font-black underline decoration-[#D02020] decoration-[3px] underline-offset-4">
                  answer and UI sync
                </span>
                .
              </p>
              <p>
                The result is a higher-quality ET concierge that stays focused
                on real Economic Times discovery instead of turning into a
                generic assistant with random finance knowledge.
              </p>
            </div>
          </div>
        </section>

        <section className="bg-[#F0F0F0] py-16 sm:py-20">
          <div className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-8">
            <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-sm font-black uppercase tracking-[0.28em] text-[#D02020]">
                  Summary
                </p>
                <h2 className="mt-3 font-black uppercase leading-none tracking-tight text-4xl sm:text-5xl">
                  7 Core Things ET Compass Provides
                </h2>
              </div>
              <p className="max-w-2xl text-base font-medium leading-relaxed sm:text-lg">
                These are the strongest user-facing capabilities the website now
                delivers.
              </p>
            </div>

            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
              {productHighlights.map((item, index) => (
                <article
                  key={item.title}
                  className="flex h-full flex-col border-4 border-black bg-white p-5 shadow-[6px_6px_0px_0px_black]"
                >
                  <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full border-2 border-black bg-black text-sm font-black text-white">
                    {index + 1}
                  </div>
                  <h3 className="font-black uppercase tracking-tight text-2xl">
                    {item.title}
                  </h3>
                  <p className="mt-4 text-base leading-relaxed text-[#333]">
                    {item.description}
                  </p>
                </article>
              ))}
            </div>

            <div className="mt-10 flex flex-wrap gap-4">
              <Link href="/search" className={`${btnPrimary} h-14 rounded-none px-7 text-base`}>
                Open Luna
              </Link>
              <Link href="/" className={`${btnSecondary} h-14 rounded-none px-7 text-base`}>
                Back to Home
              </Link>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
