import { NextResponse } from "next/server";
import { backendFetch } from "../../../lib/backend";

export async function GET() {
  const data = await backendFetch("/api/dashboard/summary");
  return NextResponse.json(data);
}
