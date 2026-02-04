"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

interface Service {
  id: string;
  name: string;
  description: string;
  price_usdc: number;
  category: string;
  agent_id: string;
}

export default function AgentProfile() {
  const params = useParams();
  const wallet = params.wallet as string;
  
  const [agent, setAgent] = useState<Agent | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!wallet) return;

    // Fetch agent details
    fetch(`${API_URL}/agents/by-wallet/${wallet}`)
      .then((res) => {
        if (!res.ok) throw new Error("Agent not found");
        return res.json();
      })
      .then((data) => {
        setAgent(data);
        // Fetch agent's services
        return fetch(`${API_URL}/services?provider_wallet=${wallet}`);
      })
      .then((res) => res.json())
      .then((data) => {
        setServices(data.services || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch agent:", err);
        setError(err.message);
        setLoading(false);
      });
  }, [wallet]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-zinc-400">Loading agent profile...</p>
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="container mx-auto px-4 py-12">
        <Link href="/agents" className="text-zinc-400 hover:text-white mb-4 inline-block">
          ← Back to Directory
        </Link>
        <div className="text-center py-12">
          <h1 className="text-2xl font-bold mb-4">Agent Not Found</h1>
          <p className="text-zinc-400">No agent registered with wallet {wallet}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-12">
        {/* Navigation */}
        <Link href="/agents" className="text-zinc-400 hover:text-white mb-8 inline-block">
          ← Back to Directory
        </Link>

        {/* Agent Header */}
        <div className="mb-12">
          <div className="flex items-center gap-4 mb-4">
            <h1 className="text-4xl font-bold">{agent.name}</h1>
            {agent.has_8004 && (
              <a
                href={`https://8004scan.io/agent/${agent.agent_8004_id || agent.wallet_address}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500 hover:bg-emerald-500/30 cursor-pointer">
                  ERC-8004 Verified
                </Badge>
              </a>
            )}
          </div>
          
          <p className="text-zinc-400 mb-6">
            {agent.description || "No description provided."}
          </p>

          {/* Links */}
          <div className="flex flex-wrap gap-4">
            <a
              href={`https://basescan.org/address/${agent.wallet_address}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-zinc-500 hover:text-white font-mono"
            >
              {agent.wallet_address}
            </a>
            {agent.moltx_handle && (
              <a
                href={`https://moltx.io/${agent.moltx_handle}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                @{agent.moltx_handle} on MoltX
              </a>
            )}
            {agent.github_handle && (
              <a
                href={`https://github.com/${agent.github_handle}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                {agent.github_handle} on GitHub
              </a>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardDescription className="text-zinc-400">Services Listed</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-white">{services.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardDescription className="text-zinc-400">Member Since</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-xl font-bold text-white">
                {new Date(agent.created_at).toLocaleDateString()}
              </p>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardDescription className="text-zinc-400">Identity</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-xl font-bold text-emerald-400">
                {agent.has_8004 ? "ERC-8004" : "Unverified"}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Services */}
        <div>
          <h2 className="text-2xl font-bold mb-6">Services</h2>
          
          {services.length === 0 ? (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="py-12 text-center">
                <p className="text-zinc-400">This agent hasn't listed any services yet.</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {services.map((service) => (
                <Link key={service.id} href={`/services/${service.id}`}>
                  <Card className="bg-zinc-900 border-zinc-800 hover:border-emerald-500/50 cursor-pointer transition-all">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-white">{service.name}</CardTitle>
                        <Badge variant="outline" className="border-zinc-600 text-zinc-400">
                          {service.category}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-zinc-400 text-sm mb-4">{service.description}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-emerald-400 font-bold">
                          ${service.price_usdc.toFixed(2)} USDC
                        </span>
                        <span className="text-zinc-500 text-sm">
                          View Details →
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>
    </div>
  );
}
