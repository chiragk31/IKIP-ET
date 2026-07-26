import type { Metadata } from "next";
import { SearchPageClient } from "./search-page-client";

export const metadata: Metadata = {
  title: "Semantic Search",
  description:
    "Hybrid semantic search across the IKIP knowledge base — combines Pinecone vector embeddings, graph expansion, and LLM reranking to answer industrial questions.",
};

export default function SearchPage() {
  return <SearchPageClient />;
}
