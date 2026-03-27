"use client";

import { getApp, getApps, initializeApp } from "firebase/app";
import {
  GoogleAuthProvider,
  browserLocalPersistence,
  getAuth,
  setPersistence,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
};

export const isFirebaseConfigured = [
  firebaseConfig.apiKey,
  firebaseConfig.authDomain,
  firebaseConfig.projectId,
  firebaseConfig.storageBucket,
  firebaseConfig.messagingSenderId,
  firebaseConfig.appId,
].every(Boolean);

function createFirebaseApp() {
  if (!isFirebaseConfigured) {
    throw new Error("Firebase web config is missing from NEXT_PUBLIC env variables.");
  }

  return getApps().length ? getApp() : initializeApp(firebaseConfig);
}

export const firebaseApp = isFirebaseConfigured ? createFirebaseApp() : null;
export const firebaseAuth = firebaseApp ? getAuth(firebaseApp) : null;
export const googleAuthProvider = new GoogleAuthProvider();

googleAuthProvider.setCustomParameters({
  prompt: "select_account",
});

let persistencePromise: Promise<void> | null = null;

export function ensureFirebasePersistence() {
  if (!firebaseAuth) return Promise.resolve();
  if (!persistencePromise) {
    persistencePromise = setPersistence(firebaseAuth, browserLocalPersistence);
  }
  return persistencePromise;
}

let analyticsPromise: Promise<void> | null = null;

export function initializeFirebaseAnalytics() {
  if (!firebaseApp || typeof window === "undefined") {
    return Promise.resolve();
  }

  if (!analyticsPromise) {
    analyticsPromise = import("firebase/analytics")
      .then(async ({ getAnalytics, isSupported }) => {
        if (await isSupported()) {
          getAnalytics(firebaseApp);
        }
      })
      .catch(() => undefined);
  }

  return analyticsPromise;
}
