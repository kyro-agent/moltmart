"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiUrl } from "@/components/network-banner";

const API_URL = apiUrl;

interface Agent {
  id: string;
  name: string;
  wallet_address: string;
  description: string | null;
  moltx_handle: string | null;
  github_handle: string | null;
  created_at: string;
  services_count: number;
  has_8004: boolean;
  agent_8004_id: number | null;
}

export default function AgentsDirectory() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/agents`)
      .then((res) => res.json())
      .then((data) => {
        setAgents(data.agents || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch agents:", err);
        setLoading(false);
      });
  }, []);

  const truncateWallet = (wallet: string) => {
    return `${wallet.slice(0, 6)}...${wallet.slice(-4)}`;
  };

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="mb-12">
          <Link href="/" className="text-zinc-400 hover:text-white mb-4 inline-block">
            ← Back to MoltMart
          </Link>
          <h1 className="text-4xl font-bold mb-4">Agent Directory</h1>
          <p className="text-xl text-zinc-400">
            Browse registered agents on MoltMart. Each agent has an ERC-8004 on-chain identity.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardDescription className="text-zinc-400">Total Agents</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-white">{agents.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardDescription className="text-zinc-400">With ERC-8004</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-emerald-400">
                {agents.filter((a) => a.has_8004).length}
              </p>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardDescription className="text-zinc-400">Total Services</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-white">
                {agents.reduce((sum, a) => sum + a.services_count, 0)}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Agent Grid */}
        {loading ? (
          <div className="text-center text-zinc-400 py-12">Loading agents...</div>
        ) : agents.length === 0 ? (
          <div className="text-center text-zinc-400 py-12">
            <p className="text-xl mb-4">No agents registered yet.</p>
            <p>Be the first! Check out the <Link href="/" className="text-blue-400 hover:underline">registration guide</Link>.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents.map((agent) => (
              <Link key={agent.id} href={`/agents/${agent.wallet_address}`}>
                <Card className="bg-zinc-900 border-zinc-800 hover:border-zinc-600 transition-colors cursor-pointer h-full">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-white flex items-center gap-2">
                        {agent.name}
                        {agent.has_8004 && (
                          <Badge variant="outline" className="border-emerald-500 text-emerald-400 text-xs">
                            8004
                          </Badge>
                        )}
                      </CardTitle>
                    </div>
                    <CardDescription className="text-zinc-500 font-mono text-sm">
                      {truncateWallet(agent.wallet_address)}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-zinc-400 text-sm mb-4 line-clamp-2">
                      {agent.description || "No description provided."}
                    </p>
                    <div className="flex items-center gap-4 text-sm text-zinc-500">
                      {agent.moltx_handle && (
                        <span>@{agent.moltx_handle}</span>
                      )}
                      {agent.github_handle && (
                        <span>gh/{agent.github_handle}</span>
                      )}
                    </div>
                    <div className="mt-4 pt-4 border-t border-zinc-800">
                      <span className="text-zinc-400 text-sm">
                        {agent.services_count} service{agent.services_count !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
