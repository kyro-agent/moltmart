"use client";

import { useState } from "react";

export function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div 
      className="bg-black rounded-xl p-4 max-w-xl mx-auto shadow-xl cursor-pointer hover:bg-zinc-900 transition group"
      onClick={handleCopy}
    >
      <code className="text-emerald-400 font-mono text-sm md:text-base select-all block">
        {command}
      </code>
      <p className="text-zinc-500 text-xs mt-2 group-hover:text-zinc-400 transition">
        {copied ? "✓ Copied!" : "👆 click to copy"}
      </p>
    </div>
  );
}
