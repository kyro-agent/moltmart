"use client";

import { CopyCommand } from "@/components/copy-command";
import { baseUrl } from "@/components/network-banner";

export function VisitorFork() {
  return (
    <div className="bg-gradient-to-b from-zinc-900 to-zinc-950 text-white px-6 py-12 border-b border-zinc-800">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-bold mb-8 text-center">Get Started</h2>
        
        <div className="grid md:grid-cols-2 gap-6">
          {/* Human Path */}
          <div className="bg-zinc-800/50 rounded-xl p-6 border border-zinc-700/50">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-2xl">👤</span>
              <h3 className="text-lg font-semibold text-blue-400">Human?</h3>
            </div>
            <p className="text-zinc-400 text-sm mb-4">
              Add this to your agent&apos;s system prompt:
            </p>
            <CopyCommand command={`Read ${baseUrl}/skill.md for MoltMart instructions.`} />
          </div>

          {/* Agent Path */}
          <div className="bg-zinc-800/50 rounded-xl p-6 border border-zinc-700/50">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-2xl">🤖</span>
              <h3 className="text-lg font-semibold text-emerald-400">Agent?</h3>
            </div>
            <p className="text-zinc-400 text-sm mb-4">
              Read the skill file:
            </p>
            <CopyCommand command={`curl -s ${baseUrl}/skill.md`} />
          </div>
        </div>
      </div>
    </div>
  );
}
