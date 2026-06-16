import { NextResponse } from "next/server";
import { getMessages } from "@/lib/db";

export async function GET() {
  try {
    const messages = getMessages();
    return NextResponse.json(messages);
  } catch (error) {
    return NextResponse.json(
      { error: String(error) },
      { status: 500 }
    );
  }
}
