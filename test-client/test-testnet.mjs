/**
 * Test MoltMart TESTNET registration flow
 */
import { privateKeyToAccount } from 'viem/accounts';
import fs from 'fs';
import path from 'path';

const keyPath = path.join(process.env.HOME, '.openclaw/workspace/.kyro-wallet-key');
const privateKey = fs.readFileSync(keyPath, 'utf8').trim();
const account = privateKeyToAccount(privateKey);

const API_URL = 'https://testnet-api.moltmart.app';

console.log(`Wallet: ${account.address}`);

// Get challenge
console.log('\n1. Getting challenge...');
const challengeRes = await fetch(`${API_URL}/agents/challenge`);
const { challenge } = await challengeRes.json();
console.log(`   Challenge: "${challenge}"`);

// Sign
console.log('\n2. Signing...');
const signature = await account.signMessage({ message: challenge });
console.log(`   Signature: ${signature.slice(0, 30)}...`);

// Register
console.log('\n3. Registering on TESTNET...');
const regRes = await fetch(`${API_URL}/agents/register`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Kyro-Testnet',
    wallet_address: account.address,
    signature: signature,
    description: 'Testing MoltMart testnet flow',
  }),
});

console.log(`   Status: ${regRes.status}`);
const result = await regRes.json();
console.log(`   Response: ${JSON.stringify(result, null, 2)}`);

if (result.api_key) {
  console.log('\n✅ REGISTERED ON TESTNET!');
  console.log(`   API Key: ${result.api_key}`);
  // Save testnet key
  fs.writeFileSync(
    path.join(process.env.HOME, '.openclaw/workspace/.moltmart-testnet-api-key'),
    result.api_key,
    { mode: 0o600 }
  );
}
