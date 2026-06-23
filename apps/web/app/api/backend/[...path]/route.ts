export const runtime = "edge";

const BACKEND = "https://api.theworldagency.uk/handholding";

async function proxy(req: Request, params: Promise<{ path: string[] }>) {
  const { path } = await params;
  const url = `${BACKEND}/${path.join("/")}`;
  const init: RequestInit = { method: req.method, headers: { "Content-Type": "application/json" } };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }
  try {
    const r = await fetch(url, init);
    const data = await r.text();
    return new Response(data, { status: r.status, headers: { "Content-Type": "application/json" } });
  } catch (e: any) {
    return Response.json({ error: String(e) }, { status: 502 });
  }
}

export async function GET(req: Request, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, params);
}
export async function POST(req: Request, { params }: { params: Promise<{ path: string[] }> }) {
  return proxy(req, params);
}
