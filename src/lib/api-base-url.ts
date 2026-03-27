const LOCAL_API_BASE_URL = "http://127.0.0.1:8000";

function normalizeUrl(value: string) {
  return value.trim().replace(/\/+$/, "");
}

export function getApiBaseUrl() {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      const localConfigured = process.env.NEXT_PUBLIC_LOCAL_API_BASE_URL;
      if (localConfigured && localConfigured.trim()) {
        return normalizeUrl(localConfigured);
      }
      return LOCAL_API_BASE_URL;
    }
  }

  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (configured && configured.trim()) {
    return normalizeUrl(configured);
  }

  return "";
}

export function getApiConfigurationError() {
  return "NEXT_PUBLIC_API_BASE_URL is missing for this deployment. Set it in Vercel to your Render backend URL and redeploy the frontend.";
}
