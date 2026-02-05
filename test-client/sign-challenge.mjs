/**
 * Sign a challenge message for MoltMart registration.
 * Usage: node sign-challenge.mjs "challenge message"
 */

import { privateKeyToAccount } from 'viem/accounts';
import fs from 'fs';
import path from 'path';

const challenge = process.argv[2] || "MoltMart Registration: I own this wallet and have an ERC-8004 identity";

// Load private key
const keyPath = path.join(process.env.HOME, '.openclaw/workspace/.kyro-wallet-key');
const privateKey = fs.readFileSync(keyPath, 'utf8').trim();

const account = privateKeyToAccount(privateKey);

console.log(`Wallet: ${account.address}`);
console.log(`Challenge: "${challenge}"`);

const signature = await account.signMessage({ message: challenge });
console.log(`Signature: ${signature}`);
