import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "../../../lib/backend";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const data = await backendFetch("/api/sync/run", { method: "POST", body: JSON.stringify(body) });
  return NextResponse.json(data);
}
