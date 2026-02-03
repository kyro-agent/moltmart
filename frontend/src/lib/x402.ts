import { x402ResourceServer, HTTPFacilitatorClient } from "@x402/core/server";
import { registerExactEvmScheme } from "@x402/evm/exact/server";

// Kyro's wallet for receiving payments
export const payTo = "0xf25896f67f849091f6d5bfed7736859aa42427b4";

// MoltMart's own facilitator (supports Base mainnet)
const facilitatorUrl = process.env.FACILITATOR_URL || "https://lasting-replacing-fundamental-bulletin.trycloudflare.com";

// Create facilitator client
const facilitatorClient = new HTTPFacilitatorClient({
  url: facilitatorUrl
});

// Create and configure x402 resource server
export const server = new x402ResourceServer(facilitatorClient);
registerExactEvmScheme(server);
