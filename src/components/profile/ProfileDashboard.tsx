"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useFirebaseAuth } from "@/components/auth/FirebaseAuthProvider";
import { JourneyPathMap } from "@/components/journey/JourneyPathMap";
import type { JourneyEvent, PathNode, SessionDocument } from "@/components/search/types";
import { getApiBaseUrl } from "@/lib/api-base-url";
const STORAGE_KEY = "et-compass-luna-chat-state";

function BrandMark() {
  return (
    <div className="flex items-center gap-2">
      <div className="h-7 w-7 rounded-full border-2 border-black bg-[#D02020]" />
      <div className="h-7 w-7 border-2 border-black bg-[#1040C0]" />
      <div
        className="h-7 w-7 border-2 border-black bg-[#F0C020]"
        style={{ clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)" }}
      />
    </div>
  );
}

function readString(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function extractStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => readString(item))
    .filter((item): item is string => Boolean(item));
}

function extractPathSnapshot(value: unknown) {
  if (typeof value !== "object" || value === null) return null;
  const record = value as Record<string, unknown>;

  const nodes: PathNode[] = [];

  if (Array.isArray(record.nodes)) {
    for (const item of record.nodes) {
      if (typeof item !== "object" || item === null) continue;
      const node = item as Record<string, unknown>;
      const id = readString(node.id);
      const label = readString(node.label);
      const detail = readString(node.detail);
      if (!id || !label || !detail) continue;
      nodes.push({
        id,
        label,
        detail,
        accent: readString(node.accent),
      });
    }
  }

  return {
    query: readString(record.query),
    route: readString(record.route),
    current_lane: readString(record.current_lane),
    primary_product: readString(record.primary_product),
    primary_display_product: readString(record.primary_display_product),
    secondary_products: extractStringArray(record.secondary_products),
    signals: extractStringArray(record.signals),
    next_action: readString(record.next_action),
    summary: readString(record.summary),
    nodes,
  };
}

function prettyLabel(value?: string | null) {
  if (!value) return "Not captured yet";
  return value.replaceAll("_", " ");
}

function formatDateTime(value?: string | null) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString([], {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

function extractSessionDocument(data: unknown): SessionDocument | null {
  if (typeof data !== "object" || data === null) return null;
  const record = data as Record<string, unknown>;
  const sessionId = readString(record.session_id);
  const title = readString(record.title);
  if (!sessionId || !title) return null;

  const profile =
    typeof record.profile === "object" && record.profile !== null
      ? (record.profile as Record<string, unknown>)
      : {};

  const journeyHistory = Array.isArray(record.journey_history)
    ? record.journey_history
        .map((item) => {
          if (typeof item !== "object" || item === null) return null;
          const event = item as Record<string, unknown>;
          return {
            timestamp: readString(event.timestamp),
            route: readString(event.route),
            user_message: readString(event.user_message),
            assistant_message: readString(event.assistant_message),
            recommendations: extractStringArray(event.recommendations),
            recommended_products: extractStringArray(event.recommended_products),
            verification_notes: extractStringArray(event.verification_notes),
            chips: extractStringArray(event.chips),
            visual_hint: readString(event.visual_hint),
            path_snapshot: extractPathSnapshot(event.path_snapshot),
          } satisfies JourneyEvent;
        })
        .filter(Boolean) as JourneyEvent[]
    : [];

  return {
    session_id: sessionId,
    title,
    profile: {
      intent: readString(profile.intent),
      sophistication: readString(profile.sophistication),
      goal: readString(profile.goal),
      profession: readString(profile.profession),
      age_range: readString(profile.age_range),
      interests: extractStringArray(profile.interests),
      existing_products: extractStringArray(profile.existing_products),
      onboarding_complete:
        typeof profile.onboarding_complete === "boolean"
          ? profile.onboarding_complete
          : undefined,
    },
    onboarding_complete: Boolean(record.onboarding_complete),
    questions_asked: extractStringArray(record.questions_asked),
    messages: [],
    journey_history: journeyHistory,
    recommendations: extractStringArray(record.recommendations),
    recommended_products: extractStringArray(record.recommended_products),
    response_type: readString(record.response_type),
    updated_at: readString(record.updated_at),
  };
}

export function ProfileDashboard() {
  const router = useRouter();
  const { user, authLoading, isConfigured, logout } = useFirebaseAuth();
  const [session, setSession] = useState<SessionDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [signOutBusy, setSignOutBusy] = useState(false);

  useEffect(() => {
    if (authLoading) {
      return;
    }

    if (!user) {
      setSession(null);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const apiBaseUrl = getApiBaseUrl();

    if (!apiBaseUrl) {
      setSession(null);
      setLoading(false);
      return;
    }

    async function loadDashboard() {
      try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        const parsed = raw ? (JSON.parse(raw) as Record<string, unknown>) : null;
        const sessionId =
          parsed && typeof parsed.activeThreadId === "string"
            ? parsed.activeThreadId
            : undefined;

        if (!sessionId) {
          setSession(null);
          return;
        }

        const sessionResponse = await fetch(`${apiBaseUrl}/sessions/${sessionId}`, {
          signal: controller.signal,
        });
        if (!sessionResponse.ok) throw new Error("Failed to fetch session document");

        const data = await sessionResponse.json();
        if (!controller.signal.aborted) {
          setSession(extractSessionDocument(data));
        }
      } catch {
        if (!controller.signal.aborted) {
          setSession(null);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadDashboard();

    return () => controller.abort();
  }, [authLoading, user]);

  const latestJourney = session?.journey_history.at(-1);
  const latestPathSnapshot = latestJourney?.path_snapshot;
  const summaryCards = useMemo(
    () => [
      { label: "Persona", value: prettyLabel(session?.profile.profession), accent: "bg-[#D02020]" },
      { label: "Goal", value: prettyLabel(session?.profile.goal), accent: "bg-[#1040C0]" },
      {
        label: "Sophistication",
        value: prettyLabel(session?.profile.sophistication),
        accent: "bg-[#F0C020]",
      },
      {
        label: "Current Lane",
        value:
          session?.recommended_products?.[0] ||
          latestJourney?.recommended_products?.[0] ||
          "ET Compass",
        accent: "bg-[#121212]",
      },
    ],
    [latestJourney?.recommended_products, session?.profile.goal, session?.profile.profession, session?.profile.sophistication, session?.recommended_products]
  );
  const latestRoute = prettyLabel(latestPathSnapshot?.route || latestJourney?.route);
  const currentLane =
    latestPathSnapshot?.primary_display_product ||
    session?.recommended_products?.[0] ||
    latestJourney?.recommended_products?.[0] ||
    "ET Compass";
  const signalCount = Math.max(
    latestPathSnapshot?.nodes?.length || 0,
    latestPathSnapshot?.signals?.length || 0
  );

  return (
    <main className="min-h-screen bg-[#F0F0F0] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1420px]">
        <header className="border-4 border-black bg-white px-5 py-5 shadow-[10px_10px_0px_0px_black] sm:px-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <Link href="/" className="inline-flex items-center gap-3">
                <BrandMark />
                <div>
                  <p className="text-[11px] font-black uppercase tracking-[0.28em] text-[#D02020]">
                    ET Compass
                  </p>
                  <p className="text-2xl font-black uppercase tracking-tight">Profile Dashboard</p>
                </div>
              </Link>
              <h1 className="mt-5 max-w-5xl text-3xl font-black uppercase leading-[0.94] sm:text-4xl xl:text-[3.3rem]">
                The live user path, profile state, and next ET opportunities in one place.
              </h1>
              <p className="mt-4 max-w-3xl text-sm font-medium leading-7 text-black/68 sm:text-base">
                This dashboard tracks how Luna is shaping the user journey, which ET lane is strongest
                right now, and what should happen next.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                href="/search"
                className="inline-flex items-center justify-center border-2 border-black bg-[#D02020] px-5 py-3 text-sm font-black uppercase tracking-[0.18em] text-white shadow-[4px_4px_0px_0px_black]"
              >
                Open Luna
              </Link>
              {user ? (
                <button
                  type="button"
                  onClick={async () => {
                    setSignOutBusy(true);
                    try {
                      await logout();
                      router.replace("/login");
                    } finally {
                      setSignOutBusy(false);
                    }
                  }}
                  className="inline-flex items-center justify-center border-2 border-black bg-white px-5 py-3 text-sm font-black uppercase tracking-[0.18em] shadow-[4px_4px_0px_0px_black]"
                >
                  {signOutBusy ? "Signing Out" : "Sign Out"}
                </button>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="inline-flex items-center justify-center border-2 border-black bg-white px-5 py-3 text-sm font-black uppercase tracking-[0.18em] shadow-[4px_4px_0px_0px_black]"
                  >
                    Login
                  </Link>
                  <Link
                    href="/signup"
                    className="inline-flex items-center justify-center border-2 border-black bg-[#F0C020] px-5 py-3 text-sm font-black uppercase tracking-[0.18em] shadow-[4px_4px_0px_0px_black]"
                  >
                    Sign Up
                  </Link>
                </>
              )}
            </div>
          </div>
        </header>

        {!isConfigured ? (
          <section className="mt-8 border-4 border-black bg-[#FFF7D4] px-5 py-5 shadow-[10px_10px_0px_0px_black] sm:px-7">
            <p className="text-[11px] font-black uppercase tracking-[0.24em] text-[#D02020]">
              Firebase Setup Needed
            </p>
            <p className="mt-3 text-lg font-medium leading-8 text-black/75">
              The profile dashboard is ready, but the app is missing the
              `NEXT_PUBLIC_FIREBASE_*` environment variables locally.
            </p>
          </section>
        ) : null}

        {!authLoading && !user ? (
          <section className="mt-8 border-4 border-black bg-white px-5 py-8 shadow-[10px_10px_0px_0px_black] sm:px-7">
            <p className="text-[11px] font-black uppercase tracking-[0.24em] text-[#D02020]">
              Account Required
            </p>
            <h2 className="mt-3 text-3xl font-black uppercase sm:text-4xl">
              Login to view the real ET profile dashboard.
            </h2>
            <p className="mt-4 max-w-3xl text-lg font-medium leading-8 text-black/72">
              Firebase authentication is now connected. Sign in first, then this page will show
              the signed-in account plus the latest Luna journey from this browser.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/login"
                className="inline-flex items-center justify-center border-2 border-black bg-[#D02020] px-5 py-3 text-sm font-black uppercase tracking-[0.18em] text-white shadow-[4px_4px_0px_0px_black]"
              >
                Login
              </Link>
              <Link
                href="/signup"
                className="inline-flex items-center justify-center border-2 border-black bg-[#F0C020] px-5 py-3 text-sm font-black uppercase tracking-[0.18em] shadow-[4px_4px_0px_0px_black]"
              >
                Sign Up
              </Link>
            </div>
          </section>
        ) : null}

        {user ? (
        <div className="mt-8 space-y-8">
          <div className="grid gap-8 xl:grid-cols-[380px_minmax(0,1fr)]">
            <section className="border-4 border-black bg-white p-5 shadow-[10px_10px_0px_0px_black] sm:p-6">
              <div className="flex items-start justify-between gap-3 border-b-4 border-black pb-5">
                <div>
                  <p className="text-[11px] font-black uppercase tracking-[0.28em] text-[#D02020]">
                    Demographic Summary
                  </p>
                  <h2 className="mt-2 text-2xl font-black uppercase leading-tight sm:text-3xl">
                    User profile snapshot
                  </h2>
                </div>
                <span className="border-2 border-black bg-[#F0F0F0] px-3 py-2 text-[10px] font-black uppercase tracking-[0.18em]">
                  {loading
                    ? "Loading"
                    : session?.onboarding_complete
                      ? "Ready"
                      : "Needs more answers"}
                </span>
              </div>

              <div className="mt-6 border-2 border-black bg-[#FFF7D4] px-4 py-4">
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-[#D02020]">
                  Firebase Account
                </p>
                <div className="mt-3 grid gap-3">
                  <div className="border border-black bg-white px-3 py-3">
                    <p className="text-[10px] font-black uppercase tracking-[0.16em] text-black/55">
                      Display Name
                    </p>
                    <p className="mt-2 text-sm font-black uppercase">
                      {user.displayName || "No display name yet"}
                    </p>
                  </div>
                  <div className="border border-black bg-white px-3 py-3">
                    <p className="text-[10px] font-black uppercase tracking-[0.16em] text-black/55">
                      Email
                    </p>
                    <p className="mt-2 break-all text-sm font-black">
                      {user.email || "No email found"}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-6 grid gap-3">
                {summaryCards.map((item) => (
                  <div
                    key={item.label}
                    className="border-2 border-black bg-[#F8F8F8] px-4 py-4 shadow-[4px_4px_0px_0px_black]"
                  >
                    <span className={`block h-1.5 w-16 ${item.accent}`} />
                    <p className="mt-3 text-[11px] font-black uppercase tracking-[0.18em] text-black/55">
                      {item.label}
                    </p>
                    <p className="mt-2 text-base font-black uppercase leading-6">{item.value}</p>
                  </div>
                ))}
              </div>

              <div className="mt-6 grid gap-4">
                <div className="border-2 border-black bg-[#FFF7D4] p-4">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-[#D02020]">
                    Interests
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(session?.profile.interests || []).length > 0 ? (
                      session?.profile.interests?.map((interest) => (
                        <span
                          key={interest}
                          className="border border-black bg-white px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.14em]"
                        >
                          {prettyLabel(interest)}
                        </span>
                      ))
                    ) : (
                      <p className="text-sm font-medium text-black/68">
                        Interests will appear here as Luna learns more.
                      </p>
                    )}
                  </div>
                </div>

                <div className="border-2 border-black bg-[#DDE7FF] p-4">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-[#1040C0]">
                    Recommended ET Lanes
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(session?.recommended_products || []).length > 0 ? (
                      session?.recommended_products?.map((product) => (
                        <span
                          key={product}
                          className="border border-black bg-white px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.14em]"
                        >
                          {product}
                        </span>
                      ))
                    ) : (
                      <p className="text-sm font-medium text-black/68">
                        Luna will surface ET products here once the user path becomes clearer.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </section>

            <section className="border-4 border-black bg-white p-5 shadow-[10px_10px_0px_0px_black] sm:p-6">
              <div className="flex flex-col gap-4 border-b-4 border-black pb-5 lg:flex-row lg:items-end lg:justify-between">
                <div>
                  <p className="text-[11px] font-black uppercase tracking-[0.28em] text-[#D02020]">
                    Current Session Pulse
                  </p>
                  <h2 className="mt-2 text-2xl font-black uppercase leading-tight sm:text-3xl">
                    What Luna sees right now
                  </h2>
                  <p className="mt-3 max-w-2xl text-sm font-medium leading-7 text-black/68">
                    This panel shows the live route, the strongest ET lane, and the immediate move Luna is trying to shape from the current conversation.
                  </p>
                </div>
                <div className="grid grid-cols-3 gap-2 lg:min-w-[360px]">
                  <div className="border-2 border-black bg-[#FFF7D4] px-3 py-3 shadow-[3px_3px_0px_0px_black]">
                    <p className="text-[9px] font-black uppercase tracking-[0.16em] text-black/55">
                      Route
                    </p>
                    <p className="mt-2 text-[11px] font-black uppercase">{latestRoute}</p>
                  </div>
                  <div className="border-2 border-black bg-[#DDE7FF] px-3 py-3 shadow-[3px_3px_0px_0px_black]">
                    <p className="text-[9px] font-black uppercase tracking-[0.16em] text-black/55">
                      Active lane
                    </p>
                    <p className="mt-2 text-[11px] font-black uppercase">{currentLane}</p>
                  </div>
                  <div className="border-2 border-black bg-[#F8F8F8] px-3 py-3 shadow-[3px_3px_0px_0px_black]">
                    <p className="text-[9px] font-black uppercase tracking-[0.16em] text-black/55">
                      Path nodes
                    </p>
                    <p className="mt-2 text-[11px] font-black uppercase">{signalCount || 0}</p>
                  </div>
                </div>
              </div>

              <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
                <div className="border-2 border-black bg-[#FFF7D4] p-4 shadow-[4px_4px_0px_0px_black]">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-[#D02020]">
                    Latest Session
                  </p>
                  <p className="mt-3 text-xl font-black uppercase leading-tight">
                    {session?.title || "No active session found"}
                  </p>
                  <p className="mt-3 text-sm font-medium leading-7 text-black/72">
                    {latestJourney?.assistant_message ||
                      "Open Luna and start a conversation to populate this panel."}
                  </p>
                </div>

                <div className="border-2 border-black bg-[#F8F8F8] p-4 shadow-[4px_4px_0px_0px_black]">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-[#1040C0]">
                    Current route summary
                  </p>
                  <p className="mt-3 text-base font-black uppercase leading-6">
                    {latestPathSnapshot?.summary || "Luna is still building a stronger ET path for this user."}
                  </p>
                  {latestPathSnapshot?.next_action ? (
                    <div className="mt-4 border-2 border-black bg-white px-3 py-3 shadow-[3px_3px_0px_0px_black]">
                      <p className="text-[10px] font-black uppercase tracking-[0.16em] text-[#D02020]">
                        Next move
                      </p>
                      <p className="mt-2 text-[11px] font-black uppercase">
                        {latestPathSnapshot.next_action}
                      </p>
                    </div>
                  ) : null}
                </div>
              </div>
            </section>
          </div>

          <section className="border-4 border-black bg-white p-5 shadow-[10px_10px_0px_0px_black] sm:p-7">
            <div className="flex flex-col gap-3 border-b-4 border-black pb-5 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.28em] text-[#D02020]">
                  Journey Intelligence
                </p>
                <h2 className="mt-2 text-3xl font-black uppercase sm:text-4xl">
                  Live path map and trail
                </h2>
              </div>
              <p className="max-w-xl text-sm font-medium leading-7 text-black/68">
                This section shows how Luna is actually threading the user through ET routes over time.
              </p>
            </div>

            <div className="mt-6">
              <JourneyPathMap
                snapshot={latestPathSnapshot}
                history={session?.journey_history}
                mode="expanded"
                title="How Luna is currently framing this user"
              />
            </div>

            <div className="mt-8 grid gap-3 xl:grid-cols-2">
              {session?.journey_history?.length ? (
                session.journey_history.slice(-6).reverse().map((event, index) => (
                  <div
                    key={`${event.timestamp || "event"}-${index}`}
                    className="border-2 border-black bg-[#F8F8F8] px-4 py-4 shadow-[4px_4px_0px_0px_black]"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-[#1040C0]">
                          {prettyLabel(event.route || "product_query")}
                        </p>
                        <p className="mt-2 text-sm font-bold leading-6">
                          {event.user_message || "No user message stored"}
                        </p>
                      </div>
                      <span className="text-[10px] font-black uppercase tracking-[0.16em] text-black/48">
                        {formatDateTime(event.timestamp)}
                      </span>
                    </div>

                    {event.recommended_products?.length ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {event.recommended_products.map((product) => (
                          <span
                            key={`${event.timestamp}-${product}`}
                            className="border border-black bg-white px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em]"
                          >
                            {product}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))
              ) : (
                <div className="border-2 border-black bg-[#F8F8F8] px-4 py-5 xl:col-span-2">
                  <p className="text-sm font-medium leading-7 text-black/68">
                    No journey data yet. Start chatting with Luna and this dashboard will begin
                    capturing profile evolution and ET recommendations.
                  </p>
                </div>
              )}
            </div>
          </section>
        </div>
        ) : null}
      </div>
    </main>
  );
}
