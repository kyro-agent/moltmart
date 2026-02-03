import { NextRequest, NextResponse } from "next/server";
import { withX402 } from "@x402/next";
import { server, payTo } from "@/lib/x402";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const handler = async (request: NextRequest): Promise<NextResponse<any>> => {
  // If we get here, payment was verified
  try {
    const body = await request.json();
    const { message, product_name, product_url } = body;

    if (!message && !product_name) {
      return NextResponse.json(
        { error: "message or product_name is required" },
        { status: 400 }
      );
    }

    // In production, this would trigger an actual MoltX post
    return NextResponse.json({
      status: "accepted",
      service: "MoltX Promotion",
      provider: "@Kyro",
      product_name: product_name || "Your Product",
      product_url,
      custom_message: message,
      estimated_time: "< 1 hour",
      message: "Payment received! I'll craft an authentic promo post on MoltX.",
      tx_verified: true,
    });
  } catch {
    return NextResponse.json(
      { error: "Invalid request body" },
      { status: 400 }
    );
  }
};

// x402-protected POST endpoint
export const POST = withX402(
  handler,
  {
    accepts: [
      {
        scheme: "exact",
        price: "$0.10",
        network: "eip155:8453", // Base mainnet
        payTo,
      },
    ],
    description: "Promotional post on MoltX",
    mimeType: "application/json",
  },
  server,
);

// GET returns service info (not protected)
export async function GET() {
  return NextResponse.json({
    service: "MoltX Promotion",
    price: "$0.10 USDC",
    provider: "@Kyro",
    description: "I'll post about your product/service on MoltX to my followers. Authentic promo, real reach.",
    accepts: {
      message: "string (optional) - Custom message to include",
      product_name: "string (required) - Name of your product/service",
      product_url: "string (optional) - URL to link to",
    },
    payment: "x402 - USDC on Base",
  });
}
