export const runtime = "edge";

const BACKEND = "https://api.theworldagency.uk/handholding";

export async function GET() {
  try {
    const r = await fetch(`${BACKEND}/demo/full-automation/latest`, {
      headers: { "Content-Type": "application/json" },
    });
    const data = await r.json();
    return Response.json(data);
  } catch (e: any) {
    return Response.json({ error: String(e) }, { status: 502 });
  }
}
