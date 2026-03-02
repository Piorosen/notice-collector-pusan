const INGESTOR_BASE_URL = process.env.INGESTOR_BASE_URL || process.env.NEXT_PUBLIC_INGESTOR_BASE_URL || "http://localhost:8000";

export async function backendFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${INGESTOR_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  const contentType = res.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) {
    throw new Error(typeof body === "string" ? body : JSON.stringify(body));
  }
  return body;
}
