import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// Force dynamic rendering - don't cache at build time
export const dynamic = 'force-dynamic';

export async function GET() {
  // Check env vars at runtime (not build time)
  const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || '';
  const siteUrl = process.env.SITE_URL || process.env.NEXT_PUBLIC_SITE_URL || '';
  const isTestnet = apiUrl.includes('testnet') || siteUrl.includes('testnet') || 
                    process.env.TESTNET === 'true' || process.env.USE_TESTNET === 'true';

  const filePath = path.join(process.cwd(), 'public', 'skill.md');
  let content = fs.readFileSync(filePath, 'utf-8');
  
  if (isTestnet) {
    // Replace mainnet URLs with testnet URLs
    content = content
      .replace(/https:\/\/api\.moltmart\.app/g, 'https://testnet-api.moltmart.app')
      .replace(/https:\/\/moltmart\.app/g, 'https://testnet.moltmart.app')
      .replace(/eip155:8453/g, 'eip155:84532')
      .replace(/network: eip155:8453/g, 'network: eip155:84532  # Base Sepolia TESTNET');
    
    // Add testnet warning at the top
    const testnetWarning = `> ⚠️ **TESTNET VERSION** - Uses Base Sepolia + Test USDC. No real funds!\n> Mainnet version: https://moltmart.app/skill.md\n\n`;
    content = testnetWarning + content;
  }
  
  return new NextResponse(content, {
    headers: {
      'Content-Type': 'text/markdown; charset=utf-8',
      'Cache-Control': 'no-store',
    },
  });
}
