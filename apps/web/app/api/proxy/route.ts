export async function POST(request: Request) {
  const url = new URL(request.url);
  const path = url.searchParams.get("path") || "";
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const body = request.method !== "GET" ? await request.text() : undefined;
    const response = await fetch(`${backendUrl}${path}`, {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
      },
      body: body,
    });

    const data = await response.text();
    return new Response(data, {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (error: any) {
    console.error("Proxy error:", error);
    return new Response(
      JSON.stringify({ error: error.message || "Proxy request failed" }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const path = url.searchParams.get("path") || "";
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const response = await fetch(`${backendUrl}${path}`);
    const data = await response.text();
    return new Response(data, {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (error: any) {
    console.error("Proxy error:", error);
    return new Response(
      JSON.stringify({ error: error.message || "Proxy request failed" }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
