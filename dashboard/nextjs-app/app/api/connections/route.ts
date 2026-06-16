import { NextRequest, NextResponse } from "next/server";
import { getConnections } from "@/lib/db";

export async function GET(request: NextRequest) {
  try {
    const topOnly = request.nextUrl.searchParams.get("top") === "1";
    const connections = getConnections(topOnly);
    return NextResponse.json(connections);
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
