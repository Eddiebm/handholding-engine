export const maxDuration = 300; // 5 min — needed for long-running job start call

async function proxyRequest(request: Request, method: string): Promise<Response> {
  const url = new URL(request.url);
  const path = url.searchParams.get("path") || "";
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const body = method !== "GET" ? await request.text() : undefined;
    const upstream = await fetch(`${backendUrl}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body,
    });

    const contentType = upstream.headers.get("content-type") || "application/json";

    // Stream binary responses (video, audio, image) directly
    if (
      contentType.startsWith("video/") ||
      contentType.startsWith("audio/") ||
      contentType.startsWith("image/")
    ) {
      return new Response(upstream.body, {
        status: upstream.status,
        headers: {
          "Content-Type": contentType,
          "Cache-Control": "public, max-age=3600",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }

    const data = await upstream.text();
    return new Response(data, {
      status: upstream.status,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (error: any) {
    return new Response(
      JSON.stringify({ error: error.message || "Proxy request failed" }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}

export async function POST(request: Request) {
  return proxyRequest(request, "POST");
}

export async function GET(request: Request) {
  return proxyRequest(request, "GET");
}

export async function DELETE(request: Request) {
  return proxyRequest(request, "DELETE");
}
