"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import FloatingChatButton from "@/components/FloatingChatButton";
import { useFirebaseAuth } from "@/components/auth/FirebaseAuthProvider";
import { UserAvatar } from "@/components/UserAvatar";
import {
  etCompassContent,
  type EtCompassStatShape,
} from "@/content/etCompassContent";
import { buildSearchPromptHref } from "@/lib/luna-prompts";

type VisualShapeKind =
  | "circle"
  | "square"
  | "triangle"
  | "diamond"
  | "ring"
  | "pill"
  | "bars"
  | "target";

const btnBase =
  "inline-flex items-center justify-center border-2 border-black font-bold uppercase tracking-wider transition-all active:translate-x-[2px] active:translate-y-[2px] active:shadow-none";
const btnPrimary =
  `${btnBase} bg-[#D02020] text-white shadow-[4px_4px_0px_0px_#121212] hover:bg-[#ba1b1b]`;
const btnSecondary =
  `${btnBase} bg-white text-[#121212] shadow-[4px_4px_0px_0px_#121212] hover:bg-[#F0F0F0]`;

const heroBadgeAccents = [
  "bg-[#D02020]",
  "bg-[#1040C0]",
  "bg-[#F0C020]",
  "bg-white",
] as const;

const featureGlyphs: VisualShapeKind[] = [
  "circle",
  "triangle",
  "square",
  "diamond",
  "ring",
  "bars",
];

const featureGlyphAccents = [
  "bg-[#D02020]",
  "bg-[#F0C020]",
  "bg-[#1040C0]",
  "bg-[#D02020]",
  "bg-[#1040C0]",
  "bg-[#121212]",
] as const;

const statAccentByIndex = [
  "bg-[#D02020]",
  "bg-[#1040C0]",
  "bg-[#F0C020]",
  "bg-[#D02020]",
] as const;

const ecosystemUnderlineAccents = [
  "bg-black",
  "bg-[#1040C0]",
  "bg-[#F0C020]",
  "bg-[#D02020]",
  "bg-black",
  "bg-[#1040C0]",
] as const;

const useCaseAccents = [
  "bg-[#D02020]",
  "bg-[#F0C020]",
  "bg-white",
  "bg-[#D02020]",
] as const;

const INTRO_DURATION_MS = 7200;
const INTRO_RESHOW_AFTER_MS = 6 * 60 * 60 * 1000;
const INTRO_STORAGE_KEY = "et-compass-intro-last-shown";

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

function MiniBadge({
  label,
  accent,
}: {
  label: string;
  accent: string;
}) {
  return (
    <div
      className={`flex h-12 w-12 items-center justify-center rounded-full border-2 border-black text-xs font-black uppercase ${accent}`}
    >
      {label}
    </div>
  );
}

function ArrowRightIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  );
}

function PlayIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M8 5.5v13l10-6.5-10-6.5Z" />
    </svg>
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

function ShapeGlyph({
  kind,
  className,
}: {
  kind: VisualShapeKind | EtCompassStatShape;
  className: string;
}) {
  if (kind === "circle") {
    return <div className={`h-12 w-12 rounded-full border-2 border-black ${className}`} />;
  }

  if (kind === "square") {
    return <div className={`h-12 w-12 border-2 border-black ${className}`} />;
  }

  if (kind === "triangle") {
    return (
      <div
        className={`h-12 w-12 border-2 border-black ${className}`}
        style={{ clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)" }}
      />
    );
  }

  if (kind === "diamond") {
    return (
      <div
        className={`h-12 w-12 rotate-45 border-2 border-black ${className}`}
      />
    );
  }

  if (kind === "ring") {
    return (
      <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-black bg-white">
        <div className={`h-6 w-6 rounded-full border-2 border-black ${className}`} />
      </div>
    );
  }

  if (kind === "pill") {
    return <div className={`h-12 w-16 rounded-full border-2 border-black ${className}`} />;
  }

  if (kind === "target") {
    return (
      <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-black bg-white">
        <div className={`flex h-7 w-7 items-center justify-center rounded-full border-2 border-black ${className}`}>
          <div className="h-2.5 w-2.5 rounded-full bg-black" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-12 w-12 items-center justify-center gap-1 border-2 border-black bg-white px-1">
      <span className={`h-7 w-1.5 ${className}`} />
      <span className={`h-9 w-1.5 ${className}`} />
      <span className={`h-5 w-1.5 ${className}`} />
    </div>
  );
}

function EcosystemPreview({
  label,
  imageSrc,
  imageAlt,
}: {
  label: string;
  imageSrc: string;
  imageAlt: string;
}) {
  return (
    <div className="relative aspect-[5/4] w-full overflow-hidden border-4 border-black bg-[#D9D9D9] shadow-[6px_6px_0px_0px_black]">
      <Image
        src={imageSrc}
        alt={imageAlt}
        fill
        sizes="(max-width: 640px) 280px, (max-width: 1024px) 320px, 340px"
        className="object-contain p-5 grayscale saturate-0 contrast-125 transition-[filter,transform] duration-500 group-hover:scale-[1.02] group-hover:grayscale-0 group-hover:saturate-100 group-hover:contrast-100 sm:p-6"
      />
      <div className="absolute left-4 top-4 border-2 border-black bg-white px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.2em]">
        {label}
      </div>
    </div>
  );
}

function PosterArt({ accent }: { accent: string }) {
  return (
    <div className="relative aspect-[5/4] overflow-hidden border-4 border-black bg-[#EFEFEF]">
      <div className={`absolute inset-x-0 top-0 h-8 ${accent}`} />
      <div className="absolute inset-x-8 top-14 h-16 border-4 border-black bg-white" />
      <div className="absolute inset-x-8 top-40 h-4 bg-black" />
      <div className="absolute bottom-8 left-8 right-8 h-24 border-4 border-black bg-white" />
      <div className="absolute bottom-12 left-12 h-3 w-28 bg-black" />
      <div className="absolute bottom-12 right-12 h-3 w-16 bg-[#D02020]" />
      <div className="absolute bottom-8 left-8 h-6 w-6 border-r-4 border-t-4 border-black bg-[#F0C020]" />
      <div className="absolute right-8 top-8 h-24 w-24 border-4 border-black bg-white/55" />
    </div>
  );
}

export default function HomePage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [introState, setIntroState] = useState<"checking" | "showing" | "hidden">(
    "checking"
  );
  const ecosystemScrollRef = useRef<HTMLDivElement | null>(null);
  const { authLoading, user } = useFirebaseAuth();
  const heroDemoIsExternal = /^https?:\/\//.test(
    etCompassContent.hero.secondaryCta.href
  );
  const repoHref = etCompassContent.brand.repoCta.href;
  const repoIsExternal = /^https?:\/\//.test(repoHref);
  const brandParts = etCompassContent.brand.logoText.split(" ");
  const brandTop = brandParts[0] ?? etCompassContent.brand.logoText;
  const brandBottom = brandParts.slice(1).join(" ") || brandTop;

  function scrollEcosystem(direction: -1 | 1) {
    ecosystemScrollRef.current?.scrollBy({
      left: direction * 360,
      behavior: "smooth",
    });
  }

  function dismissIntro() {
    setIntroState("hidden");
    try {
      window.localStorage.setItem(INTRO_STORAGE_KEY, String(Date.now()));
    } catch {}
  }

  useEffect(() => {
    let nextState: "showing" | "hidden" = "showing";

    try {
      const lastShownRaw = window.localStorage.getItem(INTRO_STORAGE_KEY);
      const lastShown = lastShownRaw ? Number(lastShownRaw) : NaN;

      if (Number.isFinite(lastShown) && Date.now() - lastShown < INTRO_RESHOW_AFTER_MS) {
        nextState = "hidden";
      }
    } catch {}

    const timeout = window.setTimeout(() => {
      setIntroState(nextState);
    }, 0);

    return () => window.clearTimeout(timeout);
  }, []);

  useEffect(() => {
    if (introState !== "showing") return;

    const timeout = window.setTimeout(() => {
      dismissIntro();
    }, INTRO_DURATION_MS);

    return () => window.clearTimeout(timeout);
  }, [introState]);

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#F0F0F0] text-[#121212] selection:bg-[#F0C020] selection:text-black">
      {introState !== "hidden" ? (
        <div className="fixed inset-0 z-[120] bg-black">
          {introState === "showing" ? (
            <>
              <video
                autoPlay
                muted
                playsInline
                preload="auto"
                onEnded={dismissIntro}
                className="h-full w-full object-cover"
              >
                <source src="/INTRO.mp4" type="video/mp4" />
              </video>

              <button
                type="button"
                onClick={dismissIntro}
                className="absolute right-5 top-5 border-2 border-white bg-black/65 px-4 py-2 text-[11px] font-black uppercase tracking-[0.2em] text-white shadow-[4px_4px_0px_0px_black]"
              >
                Skip Intro
              </button>
            </>
          ) : null}
        </div>
      ) : null}

      <FloatingChatButton />

      <nav className="sticky top-0 z-50 border-b-4 border-black bg-white">
        <div className="mx-auto flex h-[78px] max-w-[1400px] items-center gap-4 px-4 sm:px-6 xl:px-8">
          <Link href="/" className="flex shrink-0 items-center gap-3 lg:min-w-[220px]">
            <LogoMark />
            <div className="leading-none">
              <span className="block text-[11px] font-black uppercase tracking-[0.28em] text-[#D02020] sm:text-xs">
                {brandTop}
              </span>
              <span className="block pt-0.5 font-black uppercase tracking-tight text-xl sm:text-[1.9rem]">
                {brandBottom}
              </span>
            </div>
          </Link>

          <div className="hidden min-w-0 flex-1 items-center justify-center gap-1 lg:flex">
            {etCompassContent.nav.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className="inline-flex h-11 items-center rounded-full px-4 text-sm font-bold uppercase tracking-[0.16em] transition-colors hover:bg-[#F4F4F4] xl:px-5"
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="hidden shrink-0 items-center gap-3 md:flex lg:min-w-[270px] lg:justify-end">
            {authLoading ? (
              <div className="h-12 w-12 animate-pulse rounded-full border-2 border-black bg-[#E8E8E8] shadow-[4px_4px_0px_0px_black]" />
            ) : user ? (
              <Link
                href="/profile"
                aria-label="Open profile dashboard"
                className="transition-transform hover:-translate-y-0.5"
              >
                <UserAvatar
                  photoURL={user.photoURL}
                  displayName={user.displayName}
                  email={user.email}
                />
              </Link>
            ) : (
              <Link
                href="/login"
                className={`${btnSecondary} h-12 rounded-full px-6 text-sm`}
              >
                Login / Signup
              </Link>
            )}
            <Link
              href={repoHref}
              target={repoIsExternal ? "_blank" : undefined}
              rel={repoIsExternal ? "noreferrer" : undefined}
              className={`${btnPrimary} h-12 gap-2 rounded-full px-5 text-sm`}
            >
              <GitHubIcon className="h-4 w-4" />
              {etCompassContent.brand.repoCta.label}
            </Link>
          </div>

          <button
            type="button"
            onClick={() => setMobileOpen((prev) => !prev)}
            className="ml-auto flex h-10 w-10 flex-col items-center justify-center gap-1.5 border-2 border-black bg-white shadow-[2px_2px_0px_0px_black] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none md:hidden"
            aria-label="Open menu"
          >
            <span className="h-0.5 w-6 bg-black" />
            <span className="h-0.5 w-6 bg-black" />
            <span className="h-0.5 w-6 bg-black" />
          </button>
        </div>

        {mobileOpen && (
          <div className="border-t-4 border-black bg-white md:hidden">
            <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:px-6">
              {etCompassContent.nav.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className="border-2 border-black px-4 py-3 font-bold uppercase tracking-wide"
                >
                  {link.label}
                </Link>
              ))}
              {authLoading ? (
                <div className="h-12 w-12 animate-pulse rounded-full border-2 border-black bg-[#E8E8E8] shadow-[4px_4px_0px_0px_black]" />
              ) : user ? (
                <Link
                  href="/profile"
                  onClick={() => setMobileOpen(false)}
                  className="flex items-center gap-3 border-2 border-black bg-[#FFF8D8] px-3 py-3 shadow-[4px_4px_0px_0px_black]"
                >
                  <UserAvatar
                    photoURL={user.photoURL}
                    displayName={user.displayName}
                    email={user.email}
                    sizeClassName="h-11 w-11"
                    className="shadow-none"
                  />
                  <div className="min-w-0">
                    <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[#D02020]">
                      Signed In
                    </p>
                    <p className="truncate text-sm font-black uppercase text-black">
                      {user.displayName || user.email || "Open Profile"}
                    </p>
                  </div>
                </Link>
              ) : (
                <Link
                  href="/login"
                  onClick={() => setMobileOpen(false)}
                  className={`${btnSecondary} justify-center px-4 py-3`}
                >
                  Login / Signup
                </Link>
              )}
              <Link
                href={repoHref}
                target={repoIsExternal ? "_blank" : undefined}
                rel={repoIsExternal ? "noreferrer" : undefined}
                onClick={() => setMobileOpen(false)}
                className={`${btnPrimary} justify-center gap-2 rounded-full px-4 py-3`}
              >
                <GitHubIcon className="h-4 w-4" />
                {etCompassContent.brand.repoCta.label}
              </Link>
            </div>
          </div>
        )}
      </nav>

      <main>
        <section className="relative overflow-hidden border-b-4 border-black bg-[#F0F0F0]">
          <div className="grid min-h-[78vh] grid-cols-1 lg:min-h-[680px] lg:grid-cols-[minmax(0,0.98fr)_minmax(0,1.02fr)]">
            <div className="relative z-10 flex min-w-0 flex-col justify-center bg-white p-6 sm:p-12 lg:border-r-4 lg:border-black lg:px-14 lg:py-16 xl:px-16 xl:py-20">
              <div className="absolute left-0 top-0 h-24 w-24 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#F0C020] opacity-50 sm:h-32 sm:w-32" />

              <div className="max-w-[38rem]">
                <p className="mb-4 text-sm font-black uppercase tracking-[0.34em] text-[#D02020] sm:text-base">
                  {etCompassContent.hero.eyebrow}
                </p>

                <h1 className="mb-5 max-w-[7.8ch] font-black uppercase leading-[0.88] tracking-[-0.055em] text-[3.35rem] sm:mb-7 sm:text-[4.2rem] lg:text-[4.65rem] xl:text-[5.2rem]">
                  {etCompassContent.hero.title}
                </h1>

                <p className="mb-7 max-w-[28rem] border-l-4 border-[#D02020] pl-4 text-lg font-medium leading-relaxed sm:mb-8 sm:border-l-8 sm:pl-6 sm:text-xl lg:text-[1.45rem]">
                  {etCompassContent.hero.description}
                </p>

                <div className="flex flex-col gap-4 sm:flex-row">
                  <Link
                    href={etCompassContent.hero.primaryCta.href}
                    className={`${btnPrimary} h-14 w-full rounded-none px-8 text-base sm:w-auto sm:text-lg`}
                  >
                    {etCompassContent.hero.primaryCta.label}
                  </Link>

                  <Link
                    href={etCompassContent.hero.secondaryCta.href}
                    target={heroDemoIsExternal ? "_blank" : undefined}
                    rel={heroDemoIsExternal ? "noreferrer" : undefined}
                    className={`${btnSecondary} h-14 w-full gap-2 rounded-none px-8 text-base sm:w-auto sm:text-lg`}
                  >
                    <PlayIcon className="h-5 w-5" />
                    {etCompassContent.hero.secondaryCta.label}
                  </Link>
                </div>

                <div className="mt-7 flex flex-col items-start gap-3 text-xs font-bold uppercase tracking-widest sm:mt-8 sm:flex-row sm:items-center sm:gap-4 sm:text-sm">
                  <div className="-space-x-2 flex">
                    {etCompassContent.hero.badgeItems.map((item, index) => (
                      <MiniBadge
                        key={item}
                        label={item}
                        accent={heroBadgeAccents[index % heroBadgeAccents.length]}
                      />
                    ))}
                  </div>
                  <span>{etCompassContent.hero.trustLine}</span>
                </div>
              </div>
            </div>

            <div className="relative min-h-[400px] w-full overflow-hidden border-4 border-black shadow-[8px_8px_0px_0px_black] lg:min-h-[680px] lg:border-l-0 xl:min-h-[700px]">
              <Image
                src="/MAIN_LEFT.png"
                alt="ET Compass hero visual"
                fill
                sizes="(max-width: 1024px) 100vw, 56vw"
                className="object-cover object-[center_60%] lg:scale-[0.94]"
                priority
              />

              <div className="absolute right-4 top-4 border-2 border-black bg-white px-3 py-2 text-[11px] font-black uppercase tracking-[0.2em] shadow-[4px_4px_0px_0px_black] sm:right-6 sm:top-6">
                {etCompassContent.hero.rightPanelBadge}
              </div>

              <div className="absolute bottom-4 left-4 border-2 border-black bg-[#F0C020] px-3 py-2 text-[11px] font-black uppercase tracking-[0.2em] shadow-[4px_4px_0px_0px_black] sm:bottom-6 sm:left-6">
                {etCompassContent.hero.bottomChip}
              </div>
            </div>
          </div>
        </section>

        <section className="border-b-4 border-black bg-[#F0F0F0] py-16 sm:py-24 lg:py-32">
          <div className="mx-auto grid max-w-7xl gap-10 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
            <div>
              <h2 className="mb-6 font-black uppercase leading-[0.95] tracking-tight text-4xl sm:text-6xl lg:text-7xl">
                {etCompassContent.introSection.title}
              </h2>
            </div>

            <div className="space-y-6 text-lg font-medium leading-relaxed sm:text-xl">
              {etCompassContent.introSection.body.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b-4 border-black bg-[#F0C020]">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 divide-y-4 divide-black md:grid-cols-2 md:divide-x-4 md:divide-y-0 lg:grid-cols-4">
              {etCompassContent.stats.map((item, index) => (
                <div
                  key={item.label}
                  className="group relative flex flex-col items-center bg-white p-8 text-center transition-colors hover:bg-[#F0F0F0] sm:p-10 lg:p-12"
                >
                  <div className="absolute left-4 top-4 flex h-9 w-9 items-center justify-center rounded-full border-2 border-black bg-black text-sm font-black text-white shadow-[3px_3px_0px_0px_#F0C020]">
                    {index + 1}
                  </div>
                  <div className="mb-4 flex h-16 w-16 items-center justify-center">
                    <ShapeGlyph
                      kind={item.shape}
                      className={`${statAccentByIndex[index % statAccentByIndex.length]} shadow-[4px_4px_0px_0px_black]`}
                    />
                  </div>
                  <div className="mb-2 font-black tracking-tighter text-3xl sm:text-4xl lg:text-5xl">
                    {item.value}
                  </div>
                  <div className="text-xs font-bold uppercase tracking-wider sm:text-sm">
                    {item.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section
          id={etCompassContent.ecosystemSection.id}
          className="border-b-4 border-black bg-[#F0F0F0] py-16 sm:py-24 lg:py-32"
        >
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-10 flex flex-col gap-6 lg:mb-14 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-4xl">
                <p className="mb-4 text-sm font-black uppercase tracking-[0.34em] text-[#D02020]">
                  {etCompassContent.ecosystemSection.eyebrow}
                </p>
                <h2 className="mb-4 font-black uppercase leading-[0.9] text-4xl sm:text-6xl lg:text-[5.5rem]">
                  {etCompassContent.ecosystemSection.title}
                </h2>
                <p className="text-sm font-bold uppercase tracking-[0.24em] sm:text-base lg:text-lg">
                  {etCompassContent.ecosystemSection.subtitle}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => scrollEcosystem(-1)}
                  className="inline-flex h-12 w-12 items-center justify-center rounded-full border-2 border-black bg-white shadow-[4px_4px_0px_0px_black] transition-transform hover:-translate-y-1"
                  aria-label="Scroll ET products left"
                >
                  <ArrowRightIcon className="h-5 w-5 rotate-180" />
                </button>
                <button
                  type="button"
                  onClick={() => scrollEcosystem(1)}
                  className="inline-flex h-12 w-12 items-center justify-center rounded-full border-2 border-black bg-[#F0C020] shadow-[4px_4px_0px_0px_black] transition-transform hover:-translate-y-1"
                  aria-label="Scroll ET products right"
                >
                  <ArrowRightIcon className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div
              ref={ecosystemScrollRef}
              className="flex snap-x snap-mandatory gap-6 overflow-x-auto pb-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            >
              {etCompassContent.ecosystemSection.cards.map((item, index) => (
                <article
                  key={item.title}
                  className="group flex min-w-[280px] max-w-[280px] snap-start flex-col border-4 border-black bg-white p-5 shadow-[8px_8px_0px_0px_black] transition-transform duration-200 hover:-translate-y-2 sm:min-w-[320px] sm:max-w-[320px] sm:p-6 lg:min-w-[340px] lg:max-w-[340px]"
                >
                  <div className="mb-5">
                    <EcosystemPreview
                      label={item.accentLabel}
                      imageSrc={item.imageSrc}
                      imageAlt={item.imageAlt}
                    />
                  </div>

                  <p className="mb-2 text-[11px] font-black uppercase tracking-[0.28em] text-[#D02020]">
                    {item.accentLabel}
                  </p>

                  <h3 className="mb-3 font-black uppercase text-2xl sm:text-[2rem]">
                    {item.title}
                  </h3>

                  <p className="mb-6 text-base font-medium leading-relaxed opacity-80 sm:text-lg">
                    {item.description}
                  </p>

                  <Link
                    href={item.href}
                    className={`${btnPrimary} mt-auto justify-center rounded-none px-5 py-3 text-sm`}
                  >
                    {item.cta}
                  </Link>

                  <a
                    href={item.learnMoreHref}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-5 w-fit"
                  >
                    <span className="inline-flex items-center gap-2 font-black uppercase tracking-tight text-xl sm:text-2xl">
                      Learn more
                      <ArrowRightIcon className="h-6 w-6" />
                    </span>
                    <span
                      className={`mt-2 block h-[5px] w-[10.25rem] ${
                        ecosystemUnderlineAccents[index % ecosystemUnderlineAccents.length]
                      }`}
                    />
                  </a>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section
          id={etCompassContent.featuresSection.id}
          className="relative border-b-4 border-black bg-[#F0F0F0] py-12 sm:py-16 lg:py-24"
        >
          <div className="absolute left-0 top-12 h-20 w-20 rounded-full bg-[#D02020] opacity-20" />
          <div className="absolute bottom-10 right-0 h-24 w-24 bg-[#1040C0] opacity-20" />

          <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-10 max-w-3xl">
              <h2 className="mb-4 font-black uppercase leading-none text-3xl sm:text-5xl lg:text-7xl">
                {etCompassContent.featuresSection.title}
              </h2>
              <p className="text-lg font-medium leading-relaxed sm:text-xl">
                {etCompassContent.featuresSection.subtitle}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
              {etCompassContent.featuresSection.items.map((feature, index) => (
                <div
                  key={feature.title}
                  className="group border-4 border-black bg-white p-6 shadow-[8px_8px_0px_0px_black] transition-transform hover:-translate-y-2 sm:p-8"
                >
                  <div className="mb-6">
                    <ShapeGlyph
                      kind={featureGlyphs[index % featureGlyphs.length]}
                      className={`${featureGlyphAccents[index % featureGlyphAccents.length]} shadow-[4px_4px_0px_0px_black]`}
                    />
                  </div>
                  <h3 className="mb-3 font-black uppercase text-2xl leading-tight">
                    {feature.title}
                  </h3>
                  <p className="text-base font-medium leading-relaxed opacity-80">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section
          id={etCompassContent.howItWorksSection.id}
          className="relative overflow-hidden border-b-4 border-black bg-white py-12 sm:py-16 lg:py-24"
        >
          <div className="absolute inset-x-0 top-0 h-6 bg-[#F0C020]" />
          <div className="mx-auto max-w-7xl px-4 pt-6 sm:px-6 lg:px-8">
            <div className="mb-12 text-center sm:mb-16">
              <h2 className="mb-4 font-black uppercase text-3xl sm:text-5xl lg:text-7xl">
                {etCompassContent.howItWorksSection.title}
              </h2>
              <p className="text-lg font-bold uppercase tracking-widest opacity-70">
                {etCompassContent.howItWorksSection.subtitle}
              </p>
            </div>

            <div className="relative">
              <div className="pointer-events-none absolute left-[12.5%] right-[12.5%] top-[82px] hidden lg:block">
                <div className="how-luna-route-line h-0 border-t-4 border-dashed border-black/50" />
                <div className="how-luna-route-box absolute top-1/2 h-6 w-10 -translate-y-1/2 border-2 border-black bg-black" />
              </div>

              <div className="relative grid grid-cols-1 gap-8 lg:grid-cols-4">
                {etCompassContent.howItWorksSection.steps.map((step, index) => (
                  <div
                    key={step.step}
                    className="relative border-4 border-black bg-[#F0F0F0] p-8 shadow-[10px_10px_0px_0px_black]"
                  >
                    <div className="mb-6 flex items-center gap-4">
                      <div
                        className={`flex h-14 w-14 items-center justify-center border-4 border-black text-xl font-black ${
                          index % 3 === 0
                            ? "bg-[#D02020]"
                            : index % 3 === 1
                              ? "bg-[#1040C0] text-white"
                              : "bg-[#F0C020]"
                        }`}
                      >
                        {step.step}
                      </div>
                      <h3 className="font-black uppercase text-2xl">{step.title}</h3>
                    </div>
                    <p className="text-lg font-medium leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="border-b-4 border-black bg-[#D02020] py-12 text-white sm:py-16 lg:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-10 max-w-3xl">
              <h2 className="mb-4 font-black uppercase text-3xl sm:text-5xl lg:text-7xl">
                {etCompassContent.benefitsSection.title}
              </h2>
              <p className="text-lg font-bold uppercase tracking-widest text-white/80">
                {etCompassContent.benefitsSection.subtitle}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
              {etCompassContent.benefitsSection.items.map((item) => (
                <div
                  key={item.title}
                  className="border-4 border-black bg-white p-6 text-[#121212] shadow-[8px_8px_0px_0px_black] sm:p-8"
                >
                  <h3 className="mb-3 font-black uppercase text-2xl leading-tight">
                    {item.title}
                  </h3>
                  <p className="text-base font-medium leading-relaxed opacity-80">
                    {item.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="overflow-hidden border-b-4 border-black bg-[#1040C0] py-12 sm:py-16 lg:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-10 sm:mb-14">
              <h2 className="font-black uppercase text-3xl text-white sm:text-5xl lg:text-7xl">
                {etCompassContent.useCasesSection.title}
              </h2>
              <div className="mt-5 h-1 w-full bg-white" />
              <p className="mt-5 max-w-3xl text-lg font-medium leading-relaxed text-white/75">
                {etCompassContent.useCasesSection.subtitle}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
              {etCompassContent.useCasesSection.cards.map((card, index) => (
                <article
                  key={card.title}
                  className="group flex h-full flex-col border-4 border-black bg-white shadow-[10px_10px_0px_0px_black] transition-transform hover:-translate-y-2"
                >
                  <div className="p-4">
                    <PosterArt accent={useCaseAccents[index % useCaseAccents.length]} />
                  </div>

                  <div className="flex flex-1 flex-col p-6">
                    <p className="mb-4 text-[11px] font-black uppercase tracking-[0.28em] text-[#D02020]">
                      {etCompassContent.brand.assistantName}
                    </p>

                    <h3 className="mb-4 font-black uppercase leading-tight text-2xl">
                      {card.title}
                    </h3>

                    <p className="mb-6 flex-1 text-base font-medium leading-relaxed opacity-80">
                      {card.description}
                    </p>

                    <Link
                      href={buildSearchPromptHref(card.prompt)}
                      className="inline-flex items-center text-base font-black uppercase"
                    >
                      {etCompassContent.finalCtaSection.buttonLabel}
                      <ArrowRightIcon className="ml-2 h-5 w-5" />
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="overflow-hidden border-b-4 border-black bg-[#F0F0F0] py-12 sm:py-16 lg:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mb-10 text-center sm:mb-14">
              <h2 className="mb-4 font-black uppercase text-3xl sm:text-5xl lg:text-7xl">
                {etCompassContent.testimonialsSection.title}
              </h2>
              <p className="text-lg font-medium leading-relaxed opacity-70">
                {etCompassContent.testimonialsSection.subtitle}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
              {etCompassContent.testimonialsSection.items.map((item, index) => (
                <div
                  key={item.quote}
                  className="border-4 border-black bg-white p-6 shadow-[8px_8px_0px_0px_black] sm:p-8"
                >
                  <div className="mb-5 flex items-center gap-3">
                    <div
                      className={`h-4 w-4 border-2 border-black ${
                        index % 3 === 0
                          ? "rounded-full bg-[#D02020]"
                          : index % 3 === 1
                            ? "bg-[#1040C0]"
                            : "bg-[#F0C020]"
                      }`}
                    />
                    <p className="text-[11px] font-black uppercase tracking-[0.24em] text-[#D02020]">
                      {etCompassContent.brand.shortTag}
                    </p>
                  </div>

                  <p className="mb-4 text-lg font-medium leading-relaxed">
                    {item.quote}
                  </p>

                  <p className="text-sm font-black uppercase tracking-wide opacity-60">
                    {item.byline}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="relative overflow-hidden border-b-4 border-black bg-[#F0C020] py-16 sm:py-24 lg:py-32">
          <div className="absolute -left-8 top-10 h-24 w-24 rounded-full border-4 border-black bg-white opacity-80" />
          <div className="absolute bottom-10 right-10 h-20 w-20 rotate-45 border-4 border-black bg-[#D02020]" />

          <div className="relative z-10 mx-auto max-w-5xl px-4 text-center sm:px-6 lg:px-8">
            <h2 className="mb-6 font-black uppercase leading-[0.92] text-4xl sm:text-6xl lg:text-8xl">
              {etCompassContent.finalCtaSection.title}
            </h2>
            <p className="mx-auto mb-10 max-w-3xl text-lg font-medium leading-relaxed sm:text-xl lg:text-2xl">
              {etCompassContent.finalCtaSection.description}
            </p>

            <div className="mx-auto flex max-w-4xl flex-col gap-4 border-4 border-black bg-white p-4 shadow-[10px_10px_0px_0px_black] sm:p-5">
              <div className="flex flex-col gap-4 md:flex-row md:items-center">
                <div className="flex-1 border-2 border-black bg-[#F7F7F7] px-4 py-4 text-left text-sm font-medium sm:text-base">
                  {etCompassContent.finalCtaSection.inputPlaceholder}
                </div>

                <Link
                  href={etCompassContent.finalCtaSection.href}
                  className={`${btnPrimary} h-14 justify-center rounded-none px-6 text-sm sm:text-base`}
                >
                  {etCompassContent.finalCtaSection.buttonLabel}
                </Link>
              </div>

              <p className="text-[11px] font-black uppercase tracking-[0.22em] text-black/60 sm:text-xs">
                {etCompassContent.finalCtaSection.helperText}
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-[#121212] py-12 text-white sm:py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-12 grid grid-cols-1 gap-12 md:grid-cols-2 xl:grid-cols-5">
            <div className="md:col-span-2">
              <div className="mb-6 flex items-center gap-2">
                <LogoMark />
                <span className="ml-2 font-black uppercase tracking-tighter text-2xl">
                  {etCompassContent.footer.brand}
                </span>
              </div>

              <p className="mb-3 text-sm font-black uppercase tracking-[0.24em] text-[#F0C020]">
                {etCompassContent.footer.assistantLine}
              </p>

              <p className="mb-8 max-w-md text-lg opacity-70">
                {etCompassContent.footer.description}
              </p>

              <div className="inline-flex border-2 border-white px-4 py-3 text-sm font-black uppercase tracking-[0.2em]">
                {etCompassContent.footer.closingLine}
              </div>
            </div>

            <div className="xl:col-span-3">
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                {etCompassContent.footer.links.map((link) => (
                  <Link
                    key={link.label}
                    href={link.href}
                    className="group flex items-center gap-2 border-2 border-white/20 px-4 py-4 font-bold uppercase tracking-wide transition-colors hover:border-[#F0C020] hover:text-[#F0C020]"
                  >
                    <span className="h-2 w-2 bg-[#D02020] opacity-0 transition-opacity group-hover:opacity-100" />
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4 border-t-4 border-white/20 pt-8 text-sm font-bold uppercase tracking-wide text-white/70 sm:flex-row sm:items-center sm:justify-between">
            <p>{etCompassContent.footer.brand}</p>
            <div className="flex flex-wrap gap-4">
              <span>{etCompassContent.footer.assistantLine}</span>
              <span>{etCompassContent.footer.closingLine}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
