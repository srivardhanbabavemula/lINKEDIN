import { NextRequest, NextResponse } from "next/server";
import { updateMessage } from "@/lib/db";

export async function PATCH(request: NextRequest) {
  try {
    const body = await request.json();
    const { id, content, status } = body;

    if (!id) {
      return NextResponse.json({ error: "Missing message id" }, { status: 400 });
    }

    const result = updateMessage(id, { content, status });
    if (result.error) {
      return NextResponse.json({ error: result.error }, { status: 403 });
    }
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
