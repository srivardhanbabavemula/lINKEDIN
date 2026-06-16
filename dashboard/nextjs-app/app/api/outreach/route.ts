import { NextRequest, NextResponse } from "next/server";
import { updateOutreachStatus } from "@/lib/db";

export async function PATCH(request: NextRequest) {
  try {
    const body = await request.json();
    const { connectionId, status } = body;

    if (!connectionId || !status) {
      return NextResponse.json(
        { error: "connectionId and status are required" },
        { status: 400 }
      );
    }

    updateOutreachStatus(connectionId, status);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
