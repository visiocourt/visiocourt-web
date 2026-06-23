import crypto from "crypto";

/**
 * Stateless one time code (OTP) tokens.
 *
 * We never store the verification code on the server. Instead we hand the
 * client a signed token that binds { email, expiresAt } and is signed with a
 * secret AND the code itself. To verify, the user supplies the code that was
 * emailed to them; we recompute the signature and compare. Without the code
 * (which only the email owner receives) the token cannot be satisfied, and the
 * email / expiry cannot be tampered with because they are HMAC signed.
 */

const SECRET =
  process.env.WAITLIST_SECRET || "dev-only-insecure-secret-change-me";

const CODE_TTL_MS = 10 * 60 * 1000; // 10 minutes

function sign(email: string, code: string, expiresAt: number): string {
  return crypto
    .createHmac("sha256", SECRET)
    .update(`${email.toLowerCase()}|${code}|${expiresAt}`)
    .digest("hex");
}

export function generateCode(): string {
  // Cryptographically strong 6 digit code (000000 - 999999).
  return crypto.randomInt(0, 1_000_000).toString().padStart(6, "0");
}

export function createToken(email: string, code: string): string {
  const expiresAt = Date.now() + CODE_TTL_MS;
  const payload = Buffer.from(
    JSON.stringify({ email: email.toLowerCase(), expiresAt }),
  ).toString("base64url");
  return `${payload}.${sign(email, code, expiresAt)}`;
}

type VerifyResult = { ok: true } | { ok: false; reason: string };

export function verifyToken(
  token: string,
  email: string,
  code: string,
): VerifyResult {
  const parts = token.split(".");
  if (parts.length !== 2) return { ok: false, reason: "Malformed token." };

  let data: { email: string; expiresAt: number };
  try {
    data = JSON.parse(Buffer.from(parts[0], "base64url").toString());
  } catch {
    return { ok: false, reason: "Malformed token." };
  }

  if (data.email !== email.toLowerCase()) {
    return { ok: false, reason: "Email does not match this code." };
  }
  if (Date.now() > data.expiresAt) {
    return { ok: false, reason: "This code has expired. Request a new one." };
  }

  const expected = sign(email, code, data.expiresAt);
  const a = Buffer.from(parts[1]);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
    return { ok: false, reason: "Incorrect code. Please try again." };
  }

  return { ok: true };
}
