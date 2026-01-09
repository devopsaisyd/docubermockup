import { API_BASE_URL } from "@/lib/config";
import { getToken } from "@/lib/auth";
import { DEMO_MODE, demoRoute } from "@/lib/demo";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  if (DEMO_MODE) {
    // demo mode: avoid backend dependency (for screenshots)
    return demoRoute(path, init) as T;
  }
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  const text = await res.text();
  const body = text ? safeJson(text) : null;
  if (!res.ok) {
    const msg =
      (body && typeof body === "object" && (body as any).detail) ||
      `Request failed (${res.status})`;
    throw new ApiError(String(msg), res.status, body);
  }
  return body as T;
}

function safeJson(text: string) {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

