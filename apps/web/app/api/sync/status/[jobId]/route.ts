import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "../../../../lib/backend";

export async function GET(_: NextRequest, { params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  const data = await backendFetch(`/api/sync/status/${jobId}`);
  return NextResponse.json(data);
}
