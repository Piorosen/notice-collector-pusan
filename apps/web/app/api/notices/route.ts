import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "../../lib/backend";

export async function GET(req: NextRequest) {
  const query = req.nextUrl.searchParams.toString();
  const data = await backendFetch(`/api/notices${query ? `?${query}` : ""}`);
  return NextResponse.json(data);
}
