"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiUrl } from "@/components/network-banner";

const API_URL = apiUrl;

interface Service {
  id: string;
  name: string;
  description: string;
  price_usdc: number;
  category: string;
  provider_name: string;
  provider_wallet: string;
  created_at: string;
  calls_count: number;
  revenue_usdc: number;
  // Storefront fields
  usage_instructions?: string;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  example_request?: Record<string, unknown>;
  example_response?: Record<string, unknown>;
}

export default function ServiceDetail() {
  const params = useParams();
  const serviceId = params.id as string;

  const [service, setService] = useState<Service | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!serviceId) return;

    fetch(`${API_URL}/services/${serviceId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Service not found");
        return res.json();
      })
      .then((data) => {
        setService(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch service:", err);
        setError(err.message);
        setLoading(false);
      });
  }, [serviceId]);

  if (loading) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        <p className="text-zinc-400">Loading service...</p>
      </main>
    );
  }

  if (error || !service) {
    return (
      <main className="min-h-screen bg-black text-white">
        <div className="container mx-auto px-4 py-12">
          <Link href="/" className="text-zinc-400 hover:text-white mb-4 inline-block">
            ← Back to Marketplace
          </Link>
          <div className="text-center py-12">
            <h1 className="text-2xl font-bold mb-4">Service Not Found</h1>
            <p className="text-zinc-400">No service with ID {serviceId}</p>
          </div>
        </div>
      </main>
    );
  }

  const hasStorefrontInfo = service.usage_instructions || service.input_schema || 
    service.output_schema || service.example_request || service.example_response;

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="container mx-auto px-4 py-12 max-w-4xl">
        {/* Navigation */}
        <Link href="/" className="text-zinc-400 hover:text-white mb-8 inline-block">
          ← Back to Marketplace
        </Link>

        {/* Service Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <h1 className="text-3xl font-bold">{service.name}</h1>
            <Badge variant="outline" className="text-zinc-400 border-zinc-700">
              {service.category}
            </Badge>
          </div>
          <p className="text-zinc-400 text-lg mb-4">{service.description}</p>
          
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="text-zinc-500">Price:</span>{" "}
              <span className="text-green-400 font-bold">${service.price_usdc} USDC</span>
            </div>
            <div>
              <span className="text-zinc-500">By:</span>{" "}
              <Link 
                href={`/agents/${service.provider_wallet}`}
                className="text-blue-400 hover:underline"
              >
                {service.provider_name}
              </Link>
            </div>
            <div>
              <span className="text-zinc-500">Calls:</span>{" "}
              <span className="text-white">{service.calls_count}</span>
            </div>
          </div>
        </div>

        {/* How to Call This Service */}
        <Card className="bg-zinc-900 border-zinc-800 mb-6">
          <CardHeader>
            <CardTitle className="text-white">📞 How to Call This Service</CardTitle>
            <CardDescription>
              Use x402 payment to call this service endpoint
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="bg-black p-4 rounded-lg text-sm overflow-x-auto text-green-400">
{`curl -X POST ${API_URL}/services/${service.id}/call \\
  -H "X-API-Key: YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '${service.example_request ? JSON.stringify(service.example_request, null, 2) : '{"your": "request"}'}'
# Returns 402 - pay $${service.price_usdc} via x402`}
            </pre>
          </CardContent>
        </Card>

        {/* Storefront Details */}
        {hasStorefrontInfo ? (
          <>
            {/* Usage Instructions */}
            {service.usage_instructions && (
              <Card className="bg-zinc-900 border-zinc-800 mb-6">
                <CardHeader>
                  <CardTitle className="text-white">📖 Usage Instructions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-invert max-w-none">
                    <pre className="whitespace-pre-wrap text-zinc-300 text-sm">
                      {service.usage_instructions}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Input/Output Schemas */}
            <div className="grid md:grid-cols-2 gap-6 mb-6">
              {service.input_schema && (
                <Card className="bg-zinc-900 border-zinc-800">
                  <CardHeader>
                    <CardTitle className="text-white text-lg">📥 Input Schema</CardTitle>
                    <CardDescription>What to send in your request</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <pre className="bg-black p-4 rounded-lg text-sm overflow-x-auto text-blue-300">
                      {JSON.stringify(service.input_schema, null, 2)}
                    </pre>
                  </CardContent>
                </Card>
              )}

              {service.output_schema && (
                <Card className="bg-zinc-900 border-zinc-800">
                  <CardHeader>
                    <CardTitle className="text-white text-lg">📤 Output Schema</CardTitle>
                    <CardDescription>What you'll receive back</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <pre className="bg-black p-4 rounded-lg text-sm overflow-x-auto text-purple-300">
                      {JSON.stringify(service.output_schema, null, 2)}
                    </pre>
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Examples */}
            <div className="grid md:grid-cols-2 gap-6 mb-6">
              {service.example_request && (
                <Card className="bg-zinc-900 border-zinc-800">
                  <CardHeader>
                    <CardTitle className="text-white text-lg">💡 Example Request</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="bg-black p-4 rounded-lg text-sm overflow-x-auto text-yellow-300">
                      {JSON.stringify(service.example_request, null, 2)}
                    </pre>
                  </CardContent>
                </Card>
              )}

              {service.example_response && (
                <Card className="bg-zinc-900 border-zinc-800">
                  <CardHeader>
                    <CardTitle className="text-white text-lg">✅ Example Response</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="bg-black p-4 rounded-lg text-sm overflow-x-auto text-green-300">
                      {JSON.stringify(service.example_response, null, 2)}
                    </pre>
                  </CardContent>
                </Card>
              )}
            </div>
          </>
        ) : (
          <Card className="bg-zinc-900 border-zinc-800 mb-6">
            <CardContent className="py-8 text-center">
              <p className="text-zinc-500">
                ⚠️ This service hasn't provided detailed usage instructions.
              </p>
              <p className="text-zinc-600 text-sm mt-2">
                Contact the provider or check their documentation for how to call this service.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Provider Info */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-white">🤖 Provider</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">{service.provider_name}</p>
                <p className="text-zinc-500 text-sm font-mono">
                  {service.provider_wallet.slice(0, 6)}...{service.provider_wallet.slice(-4)}
                </p>
              </div>
              <Link href={`/agents/${service.provider_wallet}`}>
                <span className="text-blue-400 hover:underline text-sm">
                  View Profile →
                </span>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
