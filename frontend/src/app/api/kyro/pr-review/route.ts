import { NextRequest, NextResponse } from "next/server";
import { withX402 } from "@x402/next";
import { server, payTo } from "@/lib/x402";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const handler = async (request: NextRequest): Promise<NextResponse<any>> => {
  // If we get here, payment was verified
  try {
    const body = await request.json();
    const { pr_url, focus_areas } = body;

    if (!pr_url) {
      return NextResponse.json(
        { error: "pr_url is required" },
        { status: 400 }
      );
    }

    // In production, this would trigger an actual PR review via GitHub API
    return NextResponse.json({
      status: "accepted",
      service: "PR Code Review",
      provider: "@Kyro",
      pr_url,
      focus_areas: focus_areas || ["bugs", "performance", "readability"],
      estimated_time: "< 24 hours",
      message: "Payment received! I'll review your PR and leave detailed comments on GitHub.",
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
        price: "$0.15",
        network: "eip155:8453", // Base mainnet
        payTo,
      },
    ],
    description: "Professional code review on your GitHub PR",
    mimeType: "application/json",
  },
  server,
);

// GET returns service info (not protected)
export async function GET() {
  return NextResponse.json({
    service: "PR Code Review",
    price: "$0.15 USDC",
    provider: "@Kyro",
    description: "Professional code review on your GitHub PR. I'll review your code, check for bugs, suggest improvements, and leave detailed comments.",
    accepts: {
      pr_url: "string (required) - GitHub PR URL",
      focus_areas: "string[] (optional) - Areas to focus on",
    },
    payment: "x402 - USDC on Base",
  });
}
