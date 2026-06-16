import type { DatabaseSync } from "node:sqlite";
import { DatabaseSync as DatabaseConstructor } from "node:sqlite";
import path from "path";

const OUTREACH_STATUSES = [
  "NOT_CONTACTED",
  "CONTACTED",
  "REPLIED",
  "REFERRED",
  "NO_RESPONSE",
] as const;

let db: DatabaseSync | null = null;

export function getDb(): DatabaseSync {
  if (!db) {
    const dbPath =
      process.env.DATABASE_PATH ||
      path.join(process.cwd(), "..", "..", "database", "linkedin.db");
    const resolved = path.isAbsolute(dbPath)
      ? dbPath
      : path.join(process.cwd(), "..", "..", dbPath);
    db = new DatabaseConstructor(resolved);
    db.exec("PRAGMA foreign_keys = ON");
  }
  return db;
}

export interface ConnectionRow {
  id: number;
  name: string;
  company: string;
  role: string;
  headline: string;
  linkedin_url: string;
  referral_score: number | null;
  outreach_status: string | null;
  should_contact: number | null;
  score_breakdown: string | null;
  recruiter_type: string | null;
  alumni_tags: string | null;
  job_match: string | null;
}

export interface MessageRow {
  id: number;
  connection_id: number;
  name: string;
  company: string;
  message_type: string;
  content: string;
  status: string;
  created_at: string;
  linkedin_url?: string;
}

export interface Stats {
  total_connections: number;
  contacted: number;
  replied: number;
  referred: number;
  referral_rate: number;
}

export function getConnections(topOnly = false): ConnectionRow[] {
  const database = getDb();
  const where = topOnly ? "WHERE a.should_contact = 1" : "";
  return database
    .prepare(
      `
      SELECT
        c.id, c.name, c.company, c.role, c.headline, c.linkedin_url,
        a.referral_score, a.should_contact, a.score_breakdown,
        a.recruiter_type, a.alumni_tags, a.job_match,
        COALESCE(o.status, 'NOT_CONTACTED') AS outreach_status
      FROM connections c
      LEFT JOIN analysis a ON c.id = a.connection_id
      LEFT JOIN outreach o ON c.id = o.connection_id
      ${where}
      ORDER BY a.referral_score DESC NULLS LAST, c.name ASC
      ${topOnly ? "LIMIT 10" : ""}
      `
    )
    .all() as unknown as ConnectionRow[];
}

export function getMessages(): MessageRow[] {
  const database = getDb();
  return database
    .prepare(
      `
      SELECT m.id, m.connection_id, c.name, c.company,
             m.message_type, m.content, m.status, m.created_at,
             c.linkedin_url
      FROM messages m
      JOIN connections c ON c.id = m.connection_id
      ORDER BY m.created_at DESC
      `
    )
    .all() as unknown as MessageRow[];
}

export function getStats(): Stats {
  const database = getDb();
  const total = (
    database.prepare("SELECT COUNT(*) AS cnt FROM connections").get() as unknown as {
      cnt: number;
    }
  ).cnt;
  const contacted = (
    database
      .prepare(
        "SELECT COUNT(*) AS cnt FROM outreach WHERE status IN ('CONTACTED', 'REPLIED', 'REFERRED', 'NO_RESPONSE')"
      )
      .get() as unknown as { cnt: number }
  ).cnt;
  const replied = (
    database
      .prepare(
        "SELECT COUNT(*) AS cnt FROM outreach WHERE status IN ('REPLIED', 'REFERRED')"
      )
      .get() as unknown as { cnt: number }
  ).cnt;
  const referred = (
    database
      .prepare("SELECT COUNT(*) AS cnt FROM outreach WHERE status = 'REFERRED'")
      .get() as unknown as { cnt: number }
  ).cnt;

  return {
    total_connections: total,
    contacted,
    replied,
    referred,
    referral_rate: contacted ? Math.round((referred / contacted) * 1000) / 10 : 0,
  };
}

export function updateMessage(
  id: number,
  updates: { content?: string; status?: string }
): { error?: string } {
  const database = getDb();
  const now = new Date().toISOString();

  const row = database
    .prepare("SELECT connection_id, status FROM messages WHERE id = ?")
    .get(id) as unknown as { connection_id: number; status: string } | undefined;

  if (!row) {
    return { error: "Message not found" };
  }

  // SAFETY: manual approval required — cannot skip DRAFT -> SENT
  if (updates.status === "SENT" && row.status !== "APPROVED") {
    return {
      error: "Manual approval required. Approve the message before marking as sent.",
    };
  }

  if (updates.content !== undefined) {
    database
      .prepare("UPDATE messages SET content = ?, updated_at = ? WHERE id = ?")
      .run(updates.content, now, id);
  }
  if (updates.status !== undefined) {
    database
      .prepare(
        "UPDATE messages SET status = ?, approved_at = ?, sent_at = ?, updated_at = ? WHERE id = ?"
      )
      .run(
        updates.status,
        updates.status === "APPROVED" ? now : null,
        updates.status === "SENT" ? now : null,
        now,
        id
      );

    if (updates.status === "SENT") {
      database
        .prepare(
          `
          INSERT INTO outreach (connection_id, status, message_sent, last_contacted_at, updated_at)
          VALUES (?, 'CONTACTED', 1, ?, ?)
          ON CONFLICT(connection_id) DO UPDATE SET
            status = 'CONTACTED',
            message_sent = 1,
            last_contacted_at = excluded.last_contacted_at,
            updated_at = excluded.updated_at
          `
        )
        .run(row.connection_id, now, now);
    }
  }

  return {};
}

export function getMessageForDraft(messageId: number) {
  const database = getDb();
  return database
    .prepare(
      `
      SELECT m.id, m.connection_id, m.content, m.status, c.name, c.linkedin_url
      FROM messages m
      JOIN connections c ON c.id = m.connection_id
      WHERE m.id = ?
      `
    )
    .get(messageId) as unknown as {
    id: number;
    connection_id: number;
    content: string;
    status: string;
    name: string;
    linkedin_url: string;
  } | undefined;
}

export function saveAndApproveMessage(messageId: number, content: string): void {
  const database = getDb();
  const now = new Date().toISOString();
  database
    .prepare(
      "UPDATE messages SET content = ?, status = 'APPROVED', approved_at = ?, updated_at = ? WHERE id = ?"
    )
    .run(content, now, now, messageId);
}

export function updateOutreachStatus(connectionId: number, status: string): void {
  if (!OUTREACH_STATUSES.includes(status as (typeof OUTREACH_STATUSES)[number])) {
    throw new Error(`Invalid status: ${status}`);
  }

  const database = getDb();
  const now = new Date().toISOString();
  const responseFlag = status === "REPLIED" || status === "REFERRED" ? 1 : 0;

  database
    .prepare(
      `
      INSERT INTO outreach (connection_id, status, response_received, last_response_at, updated_at)
      VALUES (?, ?, ?, ?, ?)
      ON CONFLICT(connection_id) DO UPDATE SET
        status = excluded.status,
        response_received = CASE WHEN excluded.status IN ('REPLIED', 'REFERRED') THEN 1 ELSE outreach.response_received END,
        last_response_at = CASE WHEN excluded.status IN ('REPLIED', 'REFERRED') THEN excluded.last_response_at ELSE outreach.last_response_at END,
        updated_at = excluded.updated_at
      `
    )
    .run(
      connectionId,
      status,
      responseFlag,
      responseFlag ? now : null,
      now
    );
}
