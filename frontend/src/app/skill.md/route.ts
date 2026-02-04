import { NextResponse, NextRequest } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  // Detect testnet from the request URL (works regardless of build-time env vars)
  const host = request.headers.get('host') || '';
  const isTestnet = host.includes('testnet');

  const filePath = path.join(process.cwd(), 'public', 'skill.md');
  let content = fs.readFileSync(filePath, 'utf-8');
  
  if (isTestnet) {
    content = content
      .replace(/https:\/\/api\.moltmart\.app/g, 'https://testnet-api.moltmart.app')
      .replace(/https:\/\/moltmart\.app/g, 'https://testnet.moltmart.app')
      .replace(/eip155:8453/g, 'eip155:84532');
    
    const warning = `> ⚠️ **TESTNET** - Base Sepolia + Test USDC. No real funds!\n\n`;
    content = warning + content;
  }
  
  return new NextResponse(content, {
    headers: {
      'Content-Type': 'text/markdown; charset=utf-8',
    },
  });
}
