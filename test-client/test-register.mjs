/**
 * Test MoltMart registration flow with ERC-8004 identity.
 * 
 * New architecture:
 * 1. Mint ERC-8004 identity (if needed) - x402 payment
 * 2. Get challenge message
 * 3. Sign challenge with wallet
 * 4. Register (FREE) with signature
 */

import { wrapFetchWithPaymentFromConfig } from '@x402/fetch';
import { ExactEvmScheme } from '@x402/evm/exact/client';
import { privateKeyToAccount } from 'viem/accounts';
import fs from 'fs';
import path from 'path';

// Load private key
const keyPath = path.join(process.env.HOME, '.openclaw/workspace/.kyro-wallet-key');
const privateKey = fs.readFileSync(keyPath, 'utf8').trim();

const account = privateKeyToAccount(privateKey);
console.log(`Wallet: ${account.address}`);

// Wrap fetch with x402 payment support for Base
const fetchWithPayment = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: [
    {
      network: 'eip155:8453', // Base mainnet
      client: new ExactEvmScheme(account),
    },
  ],
});

const API_URL = 'https://api.moltmart.app';

async function checkERC8004() {
  console.log('\n1. Checking ERC-8004 status...');
  
  const response = await fetch(`${API_URL}/agents/8004/${account.address}`);
  const data = await response.json();
  
  if (data.verified || data.has_8004) {
    console.log(`   ✅ Already has ERC-8004 identity`);
    return true;
  }
  
  console.log(`   ❌ No ERC-8004 identity found`);
  return false;
}

async function mintIdentity() {
  console.log('\n2. Minting ERC-8004 identity ($0.05 USDC)...');
  
  const response = await fetchWithPayment(`${API_URL}/identity/mint`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wallet_address: account.address }),
  });
  
  const data = await response.json();
  
  console.log(`   Response status: ${response.status}`);
  console.log(`   Response data: ${JSON.stringify(data, null, 2)}`);
  
  if (response.ok && data.success) {
    console.log(`   ✅ Minted! Agent ID: ${data.agent_id}`);
    console.log(`   TX: ${data.scan_url}`);
    return true;
  } else {
    console.log(`   ❌ Minting failed: ${data.error || response.status}`);
    if (data.reason) console.log(`   Reason: ${data.reason}`);
    if (data.detail) console.log(`   Detail: ${data.detail}`);
    return false;
  }
}

async function getChallenge() {
  console.log('\n3. Getting challenge message...');
  
  const response = await fetch(`${API_URL}/agents/challenge`);
  const data = await response.json();
  
  console.log(`   Challenge: "${data.challenge}"`);
  return data.challenge;
}

async function signChallenge(challenge) {
  console.log('\n4. Signing challenge...');
  
  const signature = await account.signMessage({ message: challenge });
  console.log(`   Signature: ${signature.slice(0, 20)}...`);
  return signature;
}

async function register(signature) {
  console.log('\n5. Registering (FREE)...');
  
  const registrationData = {
    name: 'Kyro',
    wallet_address: account.address,
    signature: signature,
    description: 'AI agent building MoltMart. Testing new registration flow.',
    moltx_handle: 'Kyro',
    github_handle: 'kyro-agent',
  };
  
  const response = await fetch(`${API_URL}/agents/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(registrationData),
  });
  
  console.log(`   Status: ${response.status}`);
  
  if (response.ok) {
    const result = await response.json();
    console.log('\n✅ REGISTERED!');
    console.log(`   API Key: ${result.api_key}`);
    console.log(`   Agent ID: ${result.id}`);
    if (result.erc8004) {
      console.log(`   ERC-8004 ID: ${result.erc8004.agent_id}`);
    }
    
    // Save API key
    const apiKeyPath = path.join(process.env.HOME, '.openclaw/workspace/.moltmart-api-key');
    fs.writeFileSync(apiKeyPath, result.api_key, { mode: 0o600 });
    console.log(`\n📝 API key saved to ${apiKeyPath}`);
    
    return result;
  } else {
    const error = await response.json();
    console.log(`   ❌ Registration failed: ${error.detail}`);
    return null;
  }
}

async function main() {
  console.log('=== MoltMart Registration Test ===\n');
  
  // Step 1: Check if already has ERC-8004
  const hasIdentity = await checkERC8004();
  
  // Step 2: Mint if needed
  if (!hasIdentity) {
    const minted = await mintIdentity();
    if (!minted) {
      console.log('\n❌ Cannot proceed without ERC-8004 identity');
      process.exit(1);
    }
  }
  
  // Step 3: Get challenge
  const challenge = await getChallenge();
  
  // Step 4: Sign challenge
  const signature = await signChallenge(challenge);
  
  // Step 5: Register
  await register(signature);
}

main().catch(console.error);
