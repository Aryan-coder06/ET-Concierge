"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
  updateProfile,
} from "firebase/auth";
import { useFirebaseAuth } from "@/components/auth/FirebaseAuthProvider";
import {
  ensureFirebasePersistence,
  firebaseAuth,
  googleAuthProvider,
} from "@/lib/firebase/client";

type Mode = "login" | "signup";

type Props = {
  mode: Mode;
};

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

export function AuthSplitShell({ mode }: Props) {
  const isSignup = mode === "signup";
  const router = useRouter();
  const { user, authLoading, isConfigured } = useFirebaseAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    if (!authLoading && user) {
      router.replace("/profile");
    }
  }, [authLoading, router, user]);

  function humanizeAuthError(error: unknown) {
    const message = typeof error === "object" && error !== null && "code" in error
      ? String((error as { code?: string }).code)
      : "";

    if (message.includes("email-already-in-use")) {
      return "This email is already in use. Try logging in instead.";
    }
    if (message.includes("invalid-credential") || message.includes("wrong-password")) {
      return "The email or password does not match this account.";
    }
    if (message.includes("weak-password")) {
      return "Use a stronger password with at least 6 characters.";
    }
    if (message.includes("popup-closed-by-user")) {
      return "The Google sign-in popup was closed before completing the login.";
    }
    if (message.includes("too-many-requests")) {
      return "Too many attempts were made. Wait a moment and try again.";
    }
    return "Firebase could not complete the sign-in flow right now.";
  }

  async function handleEmailAuth() {
    if (!firebaseAuth) {
      setAuthError("Firebase is not configured in the app environment.");
      return;
    }

    if (!email.trim() || !password.trim()) {
      setAuthError("Email and password are required.");
      return;
    }

    if (isSignup && password !== confirmPassword) {
      setAuthError("Password and confirm password do not match.");
      return;
    }

    setSubmitting(true);
    setAuthError("");

    try {
      await ensureFirebasePersistence();

      if (isSignup) {
        const credential = await createUserWithEmailAndPassword(
          firebaseAuth,
          email.trim(),
          password
        );

        if (fullName.trim()) {
          await updateProfile(credential.user, {
            displayName: fullName.trim(),
          });
        }
      } else {
        await signInWithEmailAndPassword(firebaseAuth, email.trim(), password);
      }

      router.replace("/profile");
    } catch (error) {
      setAuthError(humanizeAuthError(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogleAuth() {
    if (!firebaseAuth) {
      setAuthError("Firebase is not configured in the app environment.");
      return;
    }

    setSubmitting(true);
    setAuthError("");

    try {
      await ensureFirebasePersistence();
      await signInWithPopup(firebaseAuth, googleAuthProvider);
      router.replace("/profile");
    } catch (error) {
      setAuthError(humanizeAuthError(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#F0F0F0] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-[1420px] overflow-hidden border-4 border-black bg-white shadow-[12px_12px_0px_0px_black]">
        <section className="flex w-full flex-col border-r-0 border-black bg-white lg:w-[48%] lg:border-r-4">
          <div className="border-b-4 border-black px-6 py-5 sm:px-8">
            <Link href="/" className="inline-flex items-center gap-3">
              <BrandMark />
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.28em] text-[#D02020]">
                  ET Compass
                </p>
                <p className="text-2xl font-black uppercase tracking-tight">LUNA for ET</p>
              </div>
            </Link>
          </div>

          <div className="flex flex-1 flex-col justify-between px-6 py-8 sm:px-8">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.3em] text-[#D02020]">
                {isSignup ? "Create Access" : "Sign In"}
              </p>
              <h1 className="mt-3 max-w-xl text-4xl font-black uppercase leading-[0.92] sm:text-5xl">
                {isSignup ? "Create your ET concierge account." : "Welcome back to ET Compass."}
              </h1>
              <p className="mt-4 max-w-xl text-base font-medium leading-7 text-black/72 sm:text-lg">
                {isSignup
                  ? "Create your account to save profile context, recover your ET path, and keep LUNA synced across sessions."
                  : "Sign in to continue your ET journey, reopen saved threads, and keep your concierge context alive."}
              </p>

              <div className="mt-8 grid gap-4">
                {isSignup ? (
                  <label className="grid gap-2">
                    <span className="text-[11px] font-black uppercase tracking-[0.18em]">
                      Full Name
                    </span>
                    <input
                      type="text"
                      placeholder="Aryan Singh"
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      className="h-[52px] border-2 border-black px-4 text-sm font-bold outline-none placeholder:font-medium placeholder:text-black/35"
                    />
                  </label>
                ) : null}

                <label className="grid gap-2">
                  <span className="text-[11px] font-black uppercase tracking-[0.18em]">
                    Email
                  </span>
                  <input
                    type="email"
                    placeholder="you@economictimes.com"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="h-[52px] border-2 border-black px-4 text-sm font-bold outline-none placeholder:font-medium placeholder:text-black/35"
                  />
                </label>

                <label className="grid gap-2">
                  <span className="text-[11px] font-black uppercase tracking-[0.18em]">
                    Password
                  </span>
                  <input
                    type="password"
                    placeholder={isSignup ? "Create a strong password" : "Enter your password"}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="h-[52px] border-2 border-black px-4 text-sm font-bold outline-none placeholder:font-medium placeholder:text-black/35"
                  />
                </label>

                {isSignup ? (
                  <label className="grid gap-2">
                    <span className="text-[11px] font-black uppercase tracking-[0.18em]">
                      Confirm Password
                    </span>
                    <input
                      type="password"
                      placeholder="Re-enter password"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      className="h-[52px] border-2 border-black px-4 text-sm font-bold outline-none placeholder:font-medium placeholder:text-black/35"
                    />
                  </label>
                ) : null}
              </div>

              {authError ? (
                <div className="mt-5 border-2 border-black bg-[#FFE3E3] px-4 py-3 text-sm font-bold leading-6 text-[#8F1010]">
                  {authError}
                </div>
              ) : null}

              {!isConfigured ? (
                <div className="mt-5 border-2 border-black bg-[#FFF7D4] px-4 py-3 text-sm font-bold leading-6 text-black/75">
                  Firebase config is missing from the app environment. Add the
                  `NEXT_PUBLIC_FIREBASE_*` values first.
                </div>
              ) : null}

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={() => void handleEmailAuth()}
                  disabled={submitting || authLoading || !isConfigured}
                  className="inline-flex h-[52px] items-center justify-center border-2 border-black bg-[#D02020] px-6 text-sm font-black uppercase tracking-[0.18em] text-white shadow-[5px_5px_0px_0px_black]"
                >
                  {submitting ? "Please Wait" : isSignup ? "Create Account" : "Login"}
                </button>
                <button
                  type="button"
                  onClick={() => void handleGoogleAuth()}
                  disabled={submitting || authLoading || !isConfigured}
                  className="inline-flex h-[52px] items-center justify-center border-2 border-black bg-white px-6 text-sm font-black uppercase tracking-[0.18em] shadow-[5px_5px_0px_0px_black]"
                >
                  Continue with Google
                </button>
              </div>

              <div className="mt-6 flex flex-wrap items-center gap-3 text-[11px] font-black uppercase tracking-[0.18em] text-black/55">
                <span>{authLoading ? "Checking account session" : "Firebase auth connected"}</span>
                <span className="h-1.5 w-1.5 rounded-full bg-black" />
                <Link href="/search" className="text-[#1040C0]">
                  Open Luna instead
                </Link>
              </div>
            </div>

            <div className="mt-10 border-t-4 border-black pt-5">
              <p className="text-sm font-bold text-black/72">
                {isSignup ? "Already have an account?" : "Need a new account?"}{" "}
                <Link
                  href={isSignup ? "/login" : "/signup"}
                  className="font-black uppercase tracking-[0.14em] text-[#1040C0]"
                >
                  {isSignup ? "Login here" : "Create one"}
                </Link>
              </p>
            </div>
          </div>
        </section>

        <aside className="relative hidden flex-1 overflow-hidden bg-[#1040C0] lg:flex">
          <Image
            src="/SIGNUP_LOGO.png"
            alt="ET Compass authentication visual"
            fill
            priority
            sizes="50vw"
            className="object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/22 via-black/5 to-transparent" />
        </aside>
      </div>
    </main>
  );
}
