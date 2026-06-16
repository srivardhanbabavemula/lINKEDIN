import { existsSync } from "fs";
import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";
import { getMessageForDraft, saveAndApproveMessage } from "@/lib/db";

function resolvePython(projectRoot: string): string {
  const winVenv = path.join(projectRoot, ".venv", "Scripts", "python.exe");
  const unixVenv = path.join(projectRoot, ".venv", "bin", "python");
  if (existsSync(winVenv)) return winVenv;
  if (existsSync(unixVenv)) return unixVenv;
  return "python";
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { messageId, content } = body;

    if (!messageId) {
      return NextResponse.json({ error: "messageId required" }, { status: 400 });
    }

    const msg = getMessageForDraft(messageId);
    if (!msg) {
      return NextResponse.json({ error: "Message not found" }, { status: 404 });
    }

    if (msg.status === "SENT") {
      return NextResponse.json({ error: "Already sent" }, { status: 400 });
    }

    const finalContent = (content || msg.content).trim();
    if (!finalContent) {
      return NextResponse.json({ error: "Message is empty" }, { status: 400 });
    }

    saveAndApproveMessage(messageId, finalContent);

    const projectRoot = path.resolve(process.cwd(), "..", "..");
    const python = resolvePython(projectRoot);
    const script = path.join(projectRoot, "scraper", "draft_in_linkedin.py");

    const child = spawn(python, [script, "--id", String(messageId)], {
      cwd: projectRoot,
      detached: true,
      stdio: "ignore",
      windowsHide: false,
    });
    child.unref();

    return NextResponse.json({
      success: true,
      instruction:
        "LinkedIn is opening with your message ready. Read it, then TAP SEND on LinkedIn — that is your approval.",
      name: msg.name,
    });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
