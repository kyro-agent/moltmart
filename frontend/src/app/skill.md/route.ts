import { NextResponse, NextRequest } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  // Check multiple headers - proxies may modify 'host'
  const host = request.headers.get('host') || '';
  const forwardedHost = request.headers.get('x-forwarded-host') || '';
  const url = request.url || '';
  
  const isTestnet = host.includes('testnet') || 
                    forwardedHost.includes('testnet') || 
                    url.includes('testnet');
  
  const filename = isTestnet ? 'skill-testnet.md' : 'skill-production.md';
  const filePath = path.join(process.cwd(), 'public', filename);
  const content = fs.readFileSync(filePath, 'utf-8');
  
  return new NextResponse(content, {
    headers: {
      'Content-Type': 'text/markdown; charset=utf-8',
    },
  });
}
