import { NextResponse, NextRequest } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const host = request.headers.get('host') || '';
  const isTestnet = host.includes('testnet');
  
  // Serve the appropriate static file based on host
  const filename = isTestnet ? 'skill-testnet.md' : 'skill.md';
  const filePath = path.join(process.cwd(), 'public', filename);
  const content = fs.readFileSync(filePath, 'utf-8');
  
  return new NextResponse(content, {
    headers: {
      'Content-Type': 'text/markdown; charset=utf-8',
    },
  });
}
