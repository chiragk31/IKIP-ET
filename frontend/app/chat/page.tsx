import type { Metadata } from "next";
import { ChatPageClient } from "./chat-page-client";

export const metadata: Metadata = {
  title: "AI Copilot",
  description:
    "Ask natural language questions about the industrial knowledge base and get evidence-backed answers with citations.",
};

export default function ChatPage() {
  return <ChatPageClient />;
}
