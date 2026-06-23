import { Resend } from "resend";
import { createToken, generateCode } from "../token";

export const runtime = "nodejs";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const FROM = process.env.WAITLIST_FROM || "VisioCourt <onboarding@resend.dev>";

export async function POST(request: Request) {
  let body: { email?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid request." }, { status: 400 });
  }

  const email = (body.email || "").trim();
  if (!EMAIL_RE.test(email)) {
    return Response.json(
      { error: "Please enter a valid email address." },
      { status: 400 },
    );
  }

  if (!process.env.RESEND_API_KEY) {
    return Response.json(
      {
        error:
          "Email service is not configured yet. Add RESEND_API_KEY to .env.local.",
      },
      { status: 500 },
    );
  }

  const code = generateCode();
  const token = createToken(email, code);

  const resend = new Resend(process.env.RESEND_API_KEY);
  const { error } = await resend.emails.send({
    from: FROM,
    to: email,
    subject: "Your VisioCourt verification code",
    text: `Your VisioCourt waitlist verification code is ${code}. It expires in 10 minutes. If you did not request this, you can ignore this email.`,
    html: `
      <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;color:#0f172a">
        <p style="font-size:14px;letter-spacing:.08em;text-transform:uppercase;color:#5ac3dc;font-weight:600;margin:0 0 16px">VisioCourt</p>
        <h1 style="font-size:20px;margin:0 0 8px">Confirm your email</h1>
        <p style="font-size:15px;line-height:1.6;color:#475569;margin:0 0 24px">Enter this code to join the VisioCourt waitlist. It expires in 10 minutes.</p>
        <div style="font-size:34px;font-weight:700;letter-spacing:.35em;background:#f4f4f5;border:1px solid #e4e4e7;border-radius:12px;padding:18px;text-align:center">${code}</div>
        <p style="font-size:12px;color:#94a3b8;margin:24px 0 0">If you did not request this, you can safely ignore this email.</p>
      </div>
    `,
  });

  if (error) {
    return Response.json(
      { error: "Could not send the verification email. Please try again." },
      { status: 502 },
    );
  }

  // The token is safe to expose: it contains no usable code, only a signature.
  return Response.json({ token });
}
