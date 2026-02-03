/**
 * MoltMart x402 Facilitator
 * 
 * Verifies and settles x402 payments on Base mainnet.
 * Based on arc-merchant facilitator by @ortegarod
 */

import { x402Facilitator } from "@x402/core/facilitator";
import {
  PaymentPayload,
  PaymentRequirements,
  SettleResponse,
  VerifyResponse,
} from "@x402/core/types";
import { toFacilitatorEvmSigner } from "@x402/evm";
import { registerExactEvmScheme } from "@x402/evm/exact/facilitator";
import dotenv from "dotenv";
import express from "express";
import { createPublicClient, createWalletClient, http, Abi } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";

dotenv.config();

const PORT = process.env.PORT || "4022";
const BASE_NETWORK = "eip155:8453";

// Base mainnet USDC contract
const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";

// Facilitator private key (for settling transactions)
const FACILITATOR_PRIVATE_KEY = process.env.FACILITATOR_PRIVATE_KEY;

if (!FACILITATOR_PRIVATE_KEY) {
  console.error("❌ FACILITATOR_PRIVATE_KEY environment variable is required");
  console.error("   This wallet will pay gas for settlement transactions");
  process.exit(1);
}

// Create viem clients
const account = privateKeyToAccount(FACILITATOR_PRIVATE_KEY as `0x${string}`);

const publicClient = createPublicClient({
  chain: base,
  transport: http(),
});

const walletClient = createWalletClient({
  account,
  chain: base,
  transport: http(),
});

console.log(`🔐 Facilitator wallet: ${account.address}`);

// Create EVM signer for x402
const evmSigner = toFacilitatorEvmSigner({
  address: account.address,

  // Read operations
  getCode: (args: { address: `0x${string}` }) => publicClient.getCode(args),

  readContract: (args: {
    address: `0x${string}`;
    abi: readonly unknown[];
    functionName: string;
    args?: readonly unknown[];
  }) =>
    publicClient.readContract({
      ...args,
      args: args.args || [],
    } as any),

  verifyTypedData: (args: {
    address: `0x${string}`;
    domain: Record<string, unknown>;
    types: Record<string, unknown>;
    primaryType: string;
    message: Record<string, unknown>;
    signature: `0x${string}`;
  }) => publicClient.verifyTypedData(args as any),

  // Write operations
  writeContract: async (args: {
    address: `0x${string}`;
    abi: readonly unknown[];
    functionName: string;
    args: readonly unknown[];
  }): Promise<`0x${string}`> => {
    const hash = await walletClient.writeContract({
      address: args.address,
      abi: args.abi as Abi,
      functionName: args.functionName,
      args: args.args as any[],
    });
    return hash;
  },

  sendTransaction: async (args: {
    to: `0x${string}`;
    data: `0x${string}`;
  }): Promise<`0x${string}`> => {
    const hash = await walletClient.sendTransaction({
      to: args.to,
      data: args.data,
    });
    return hash;
  },

  waitForTransactionReceipt: async (args: { hash: `0x${string}` }) => {
    return publicClient.waitForTransactionReceipt(args);
  },
});

// Initialize facilitator with logging hooks
const facilitator = new x402Facilitator()
  .onBeforeVerify(async (context) => {
    console.log("📝 Verifying payment...", JSON.stringify(context, null, 2));
  })
  .onAfterVerify(async (context) => {
    console.log("✅ Payment verified");
  })
  .onVerifyFailure(async (context) => {
    console.log("❌ Verify failed:", context);
  })
  .onBeforeSettle(async (context) => {
    console.log("💸 Settling payment...");
  })
  .onAfterSettle(async (context) => {
    console.log("✅ Payment settled");
  })
  .onSettleFailure(async (context) => {
    console.log("❌ Settlement failed:", context);
  });

// Register Base mainnet with our signer
registerExactEvmScheme(facilitator, {
  signer: evmSigner,
  networks: BASE_NETWORK,
  deployERC4337WithEIP6492: false,
});

console.log(`📡 Registered network: ${BASE_NETWORK} (Base mainnet)`);

// Express app
const app = express();
app.use(express.json());

// CORS for MoltMart frontend
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.header("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") {
    return res.sendStatus(200);
  }
  next();
});

// POST /verify
app.post("/verify", async (req, res) => {
  try {
    const { paymentPayload, paymentRequirements } = req.body as {
      paymentPayload: PaymentPayload;
      paymentRequirements: PaymentRequirements;
    };

    if (!paymentPayload || !paymentRequirements) {
      return res.status(400).json({
        error: "Missing paymentPayload or paymentRequirements",
      });
    }

    const response: VerifyResponse = await facilitator.verify(
      paymentPayload,
      paymentRequirements
    );
    res.json(response);
  } catch (error) {
    console.error("Verify error:", error);
    res.status(500).json({
      error: error instanceof Error ? error.message : "Unknown error",
    });
  }
});

// POST /settle
app.post("/settle", async (req, res) => {
  try {
    const { paymentPayload, paymentRequirements } = req.body;

    if (!paymentPayload || !paymentRequirements) {
      return res.status(400).json({
        error: "Missing paymentPayload or paymentRequirements",
      });
    }

    const response: SettleResponse = await facilitator.settle(
      paymentPayload as PaymentPayload,
      paymentRequirements as PaymentRequirements
    );
    res.json(response);
  } catch (error) {
    console.error("Settle error:", error);

    if (error instanceof Error && error.message.includes("Settlement aborted:")) {
      return res.json({
        success: false,
        errorReason: error.message.replace("Settlement aborted: ", ""),
        network: req.body?.paymentPayload?.network || "unknown",
      } as SettleResponse);
    }

    res.status(500).json({
      error: error instanceof Error ? error.message : "Unknown error",
    });
  }
});

// GET /supported
app.get("/supported", async (req, res) => {
  try {
    const response = facilitator.getSupported();
    res.json(response);
  } catch (error) {
    console.error("Supported error:", error);
    res.status(500).json({
      error: error instanceof Error ? error.message : "Unknown error",
    });
  }
});

// Health check
app.get("/health", async (_req, res) => {
  res.json({
    status: "ok",
    network: BASE_NETWORK,
    wallet: account.address,
    usdc: BASE_USDC,
  });
});

// Root
app.get("/", async (_req, res) => {
  res.json({
    name: "MoltMart x402 Facilitator",
    network: BASE_NETWORK,
    endpoints: ["POST /verify", "POST /settle", "GET /supported", "GET /health"],
  });
});

// Start server
app.listen(parseInt(PORT), () => {
  console.log(`\n🚀 MoltMart x402 Facilitator running on http://localhost:${PORT}`);
  console.log(`   Network: ${BASE_NETWORK} (Base mainnet)`);
  console.log(`   Wallet: ${account.address}`);
  console.log(`   USDC: ${BASE_USDC}`);
  console.log(`   Endpoints: POST /verify, POST /settle, GET /supported, GET /health\n`);
});
