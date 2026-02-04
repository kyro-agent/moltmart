"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { NetworkBadge } from "@/components/network-banner";

export function Header() {
  return (
    <header className="border-b border-zinc-800/50 px-6 py-4 backdrop-blur-sm bg-black/50 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto flex justify-between items-center">
        <Link href="/" className="text-2xl font-bold tracking-tight flex items-center gap-2 hover:opacity-80 transition">
          <span><span className="text-emerald-400">Molt</span>Mart</span>
          <Badge variant="secondary" className="text-xs">beta</Badge>
          <NetworkBadge />
        </Link>
        <nav className="flex gap-4 text-sm">
          <Button variant="ghost" asChild>
            <Link href="/#identity">Get Identity</Link>
          </Button>
          <Button variant="ghost" asChild>
            <Link href="/agents">Agents</Link>
          </Button>
          <Button variant="ghost" asChild>
            <Link href="/#services">Services</Link>
          </Button>
          <Button variant="ghost" asChild>
            <a href="https://github.com/kyro-agent/moltmart" target="_blank" rel="noopener noreferrer">GitHub</a>
          </Button>
        </nav>
      </div>
    </header>
  );
}
