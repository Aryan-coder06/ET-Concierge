"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  onAuthStateChanged,
  signOut,
  type User,
} from "firebase/auth";
import {
  ensureFirebasePersistence,
  firebaseAuth,
  initializeFirebaseAnalytics,
  isFirebaseConfigured,
} from "@/lib/firebase/client";

type FirebaseAuthContextValue = {
  user: User | null;
  authLoading: boolean;
  isConfigured: boolean;
  logout: () => Promise<void>;
};

const FirebaseAuthContext = createContext<FirebaseAuthContextValue | null>(null);

export function FirebaseAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(isFirebaseConfigured);

  useEffect(() => {
    if (!isFirebaseConfigured || !firebaseAuth) {
      return;
    }

    const auth = firebaseAuth;
    initializeFirebaseAnalytics();

    let unsubscribe = () => {};

    void ensureFirebasePersistence().then(() => {
      unsubscribe = onAuthStateChanged(auth, (nextUser) => {
        setUser(nextUser);
        setAuthLoading(false);
      });
    });

    return () => unsubscribe();
  }, []);

  const value = useMemo<FirebaseAuthContextValue>(
    () => ({
      user,
      authLoading,
      isConfigured: isFirebaseConfigured,
      logout: async () => {
        if (!firebaseAuth) return;
        await signOut(firebaseAuth);
      },
    }),
    [authLoading, user]
  );

  return (
    <FirebaseAuthContext.Provider value={value}>
      {children}
    </FirebaseAuthContext.Provider>
  );
}

export function useFirebaseAuth() {
  const context = useContext(FirebaseAuthContext);
  if (!context) {
    throw new Error("useFirebaseAuth must be used inside FirebaseAuthProvider.");
  }
  return context;
}
