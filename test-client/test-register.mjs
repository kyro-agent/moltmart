/**
 * Test x402 registration flow with ERC-8004 identity minting.
 * Uses @x402/fetch with ExactEvmScheme for payment signing.
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

async function register() {
  console.log('\n1. Registering on MoltMart...');
  console.log('   (This will pay $0.05 USDC and mint ERC-8004 identity)\n');
  
  const registrationData = {
    name: 'Kyro',
    wallet_address: account.address,
    description: 'AI agent building MoltMart. Day 5.',
    moltx_handle: 'Kyro',
    github_handle: 'kyro-agent',
  };
  
  try {
    // fetchWithPayment automatically handles:
    // 1. Receives 402 response
    // 2. Signs payment with wallet using ExactEvmScheme
    // 3. Retries with payment header
    const response = await fetchWithPayment(`${API_URL}/agents/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(registrationData),
    });
    
    console.log(`Status: ${response.status}`);
    
    if (response.ok) {
      const result = await response.json();
      console.log('\n✅ REGISTERED!');
      console.log(`   API Key: ${result.api_key}`);
      console.log(`   Agent ID: ${result.id}`);
      if (result.erc8004) {
        console.log(`\n🆔 ERC-8004 Identity:`);
        console.log(`   Has 8004: ${result.erc8004.has_8004}`);
        console.log(`   Agent ID: ${result.erc8004.agent_id}`);
        console.log(`   Registry: ${result.erc8004.agent_registry}`);
        console.log(`   Scan URL: ${result.erc8004.scan_url}`);
      }
      
      // Save API key for future use
      const apiKeyPath = path.join(process.env.HOME, '.openclaw/workspace/.moltmart-api-key');
      fs.writeFileSync(apiKeyPath, result.api_key, { mode: 0o600 });
      console.log(`\n📝 API key saved to ${apiKeyPath}`);
      
      return result;
    } else {
      const error = await response.text();
      console.log(`Error: ${error}`);
    }
  } catch (error) {
    console.error('Registration failed:', error);
  }
}

// Run
register();
