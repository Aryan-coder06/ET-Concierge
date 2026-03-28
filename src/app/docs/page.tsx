import type { Metadata } from "next";
import DocsPage from "@/components/docs/DocsPage";

export const metadata: Metadata = {
  title: "Documentation | ET Compass",
  description:
    "How ET Compass and LUNA for ET were built: platform architecture, RAG flow, contributor roles, and core product capabilities.",
};

export default function Page() {
  return <DocsPage />;
}
