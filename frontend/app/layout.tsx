import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { AppHeader } from "@/components/app-shell/app-header";

const ibmPlexSans = IBM_Plex_Sans({
  weight: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-ibm-sans",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  weight: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-ibm-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "IKIP — Industrial Knowledge Intelligence Platform",
    template: "%s | IKIP",
  },
  description:
    "AI-powered platform that transforms industrial documents into structured organizational knowledge. Semantic search, knowledge graph, and AI Copilot for industrial teams.",
  keywords: [
    "industrial knowledge",
    "document intelligence",
    "knowledge graph",
    "semantic search",
    "AI copilot",
    "maintenance intelligence",
    "compliance",
    "industrial AI",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${ibmPlexSans.variable} ${ibmPlexMono.variable} h-full`}
    >
      <body className="min-h-full flex flex-col" style={{ backgroundColor: "#0B0E11" }}>
        <Providers>
          <AppHeader />
          {children}
        </Providers>
      </body>
    </html>
  );
}

