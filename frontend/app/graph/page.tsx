import type { Metadata } from "next";
import { GraphPageClient } from "./graph-page-client";

export const metadata: Metadata = {
  title: "Knowledge Graph Explorer",
  description:
    "Explore the IKIP Knowledge Graph — browse all extracted entities, their types, relationships, and provenance.",
};

export default function GraphPage() {
  return <GraphPageClient />;
}
