import type { Metadata } from "next";
import { HomePageClient } from "./home-page-client";

export const metadata: Metadata = {
  title: "IKIP — Industrial Knowledge Intelligence Platform",
  description:
    "Transform heterogeneous industrial documents into structured organizational knowledge. Semantic search, AI Copilot, and Knowledge Graph for industrial teams.",
};

export default function HomePage() {
  return <HomePageClient />;
}
