import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// This gets baked in at BUILD time - each Railway environment 
// builds separately with its own env vars
const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
const IS_TESTNET = API_URL.includes('testnet');

export async function GET() {
  const filename = IS_TESTNET ? 'skill-testnet.md' : 'skill-production.md';
  const filePath = path.join(process.cwd(), 'public', filename);
  const content = fs.readFileSync(filePath, 'utf-8');
  
  return new NextResponse(content, {
    headers: {
      'Content-Type': 'text/markdown; charset=utf-8',
    },
  });
}
