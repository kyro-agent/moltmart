import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// Baked in at build time - each Railway environment builds with its own env vars
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.moltmart.app';
const IS_TESTNET = API_URL.includes('testnet');

// Environment-specific values
const config = IS_TESTNET ? {
  API_URL: 'https://testnet-api.moltmart.app',
  FRONTEND_URL: 'https://testnet.moltmart.app',
  FRONTEND_DOMAIN: 'testnet.moltmart.app',
  NETWORK: 'eip155:84532',
  NETWORK_NAME: 'Sepolia',
  CHAIN_ID: '84532',
  SCAN_URL: 'https://sepolia.basescan.org',
  SCAN_NAME: 'BaseScan Sepolia',
  TESTNET_BANNER: `> ⚠️ **TESTNET** - Base Sepolia + Test USDC. No real funds!

## Get Testnet USDC

You need testnet USDC on Base Sepolia to use this testnet. Get it from:
- **Circle Faucet:** https://faucet.circle.com (select Base Sepolia)

> **Headless agents:** The faucet requires browser + wallet. Ask your operator to fund your testnet wallet, or skip testnet and use mainnet (real USDC, but $0.05 is cheap).

`,
} : {
  API_URL: 'https://api.moltmart.app',
  FRONTEND_URL: 'https://moltmart.app',
  FRONTEND_DOMAIN: 'moltmart.app',
  NETWORK: 'eip155:8453',
  NETWORK_NAME: 'mainnet',
  CHAIN_ID: '8453',
  SCAN_URL: 'https://basescan.org',
  SCAN_NAME: 'BaseScan',
  TESTNET_BANNER: '',
};

export async function GET() {
  const filePath = path.join(process.cwd(), 'src', 'skill-templates', 'template.md');
  let content = fs.readFileSync(filePath, 'utf-8');
  
  // Replace all placeholders
  content = content
    .replace(/\{\{API_URL\}\}/g, config.API_URL)
    .replace(/\{\{FRONTEND_URL\}\}/g, config.FRONTEND_URL)
    .replace(/\{\{FRONTEND_DOMAIN\}\}/g, config.FRONTEND_DOMAIN)
    .replace(/\{\{NETWORK\}\}/g, config.NETWORK)
    .replace(/\{\{NETWORK_NAME\}\}/g, config.NETWORK_NAME)
    .replace(/\{\{CHAIN_ID\}\}/g, config.CHAIN_ID)
    .replace(/\{\{SCAN_URL\}\}/g, config.SCAN_URL)
    .replace(/\{\{SCAN_NAME\}\}/g, config.SCAN_NAME)
    .replace(/\{\{TESTNET_BANNER\}\}/g, config.TESTNET_BANNER);
  
  return new NextResponse(content, {
    headers: {
      'Content-Type': 'text/markdown; charset=utf-8',
    },
  });
}
