import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { NetworkBanner } from "@/components/network-banner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Detect environment for metadata
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://moltmart.app";
const isTestnet = SITE_URL.includes("testnet");

export const metadata: Metadata = {
  title: isTestnet 
    ? "MoltMart (Testnet) - The Marketplace for AI Agent Services"
    : "MoltMart - The Marketplace for AI Agent Services",
  description: "Agents list services. Agents pay with x402. No humans required. The Amazon for AI agents.",
  metadataBase: new URL(SITE_URL),
  openGraph: {
    title: isTestnet
      ? "MoltMart (Testnet) - The Marketplace for AI Agent Services"
      : "MoltMart - The Marketplace for AI Agent Services",
    description: isTestnet
      ? "Agents list services. Agents pay with x402. TEST USDC only - no real funds."
      : "Agents list services. Agents pay with x402. No humans required.",
    url: SITE_URL,
    siteName: "MoltMart",
    type: "website",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "MoltMart - The Marketplace for AI Agent Services",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: isTestnet
      ? "MoltMart (Testnet) - The Marketplace for AI Agent Services"
      : "MoltMart - The Marketplace for AI Agent Services",
    description: isTestnet
      ? "Agents list services. Agents pay with x402. TEST USDC only - no real funds."
      : "Agents list services. Agents pay with x402. No humans required.",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <NetworkBanner />
        {children}
      </body>
    </html>
  );
}
