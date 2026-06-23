import { verifyToken } from "../token";

export const runtime = "nodejs";

const FORMSPREE =
  process.env.FORMSPREE_ENDPOINT || "https://formspree.io/f/xzdqnawr";

export async function POST(request: Request) {
  let body: { email?: string; code?: string; token?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid request." }, { status: 400 });
  }

  const email = (body.email || "").trim();
  const code = (body.code || "").trim();
  const token = body.token || "";

  if (!email || !code || !token) {
    return Response.json({ error: "Missing fields." }, { status: 400 });
  }

  const result = verifyToken(token, email, code);
  if (!result.ok) {
    return Response.json({ error: result.reason }, { status: 400 });
  }

  // Email ownership confirmed. Forward the verified address to Formspree.
  try {
    await fetch(FORMSPREE, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ email, verified: true }),
    });
  } catch {
    // Verification still succeeded for the user; capture failures are
    // non-fatal here. Logging/retry could be added later.
  }

  return Response.json({ ok: true });
}
