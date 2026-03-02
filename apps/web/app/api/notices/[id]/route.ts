import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "../../../lib/backend";

export async function GET(_: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await backendFetch(`/api/notices/${id}`);
  return NextResponse.json(data);
}
