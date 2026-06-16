"use client";

import { useCallback, useEffect, useState } from "react";

interface Connection {
  id: number;
  name: string;
  company: string;
  role: string;
  headline: string;
  linkedin_url: string;
  referral_score: number | null;
  outreach_status: string;
  score_breakdown: string | null;
  recruiter_type: string | null;
  alumni_tags: string | null;
  job_match: string | null;
}

interface Message {
  id: number;
  connection_id: number;
  name: string;
  company: string;
  message_type: string;
  content: string;
  status: string;
}

interface Stats {
  total_connections: number;
  contacted: number;
  replied: number;
  referred: number;
  referral_rate: number;
}

const OUTREACH_STATUSES = [
  "NOT_CONTACTED",
  "CONTACTED",
  "REPLIED",
  "REFERRED",
  "NO_RESPONSE",
];

function scoreBadgeClass(score: number | null): string {
  if (score === null) return "badge badge-score-low";
  if (score >= 70) return "badge badge-score-high";
  if (score >= 40) return "badge badge-score-mid";
  return "badge badge-score-low";
}

function statusBadgeClass(status: string): string {
  if (status === "DRAFT") return "badge badge-draft";
  if (status === "APPROVED") return "badge badge-approved";
  if (status === "SENT") return "badge badge-sent";
  return "badge badge-status";
}

function parseJson<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function MessageCard({
  message,
  onUpdate,
}: {
  message: Message;
  onUpdate: () => void;
}) {
  const [content, setContent] = useState(message.content);
  const [saving, setSaving] = useState(false);
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const patchMessage = async (updates: { content?: string; status?: string }) => {
    setSaving(true);
    setError(null);
    const res = await fetch(`/api/messages/${message.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: message.id, ...updates }),
    });
    const data = await res.json();
    if (!res.ok) setError(data.error || "Update failed");
    setSaving(false);
    onUpdate();
  };

  const openInLinkedIn = async () => {
    setOpening(true);
    setError(null);
    setSuccess(null);
    const res = await fetch("/api/linkedin/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messageId: message.id, content }),
    });
    const data = await res.json();
    setOpening(false);
    if (!res.ok) {
      setError(data.error || "Could not open LinkedIn. Run: python copilot.py login");
      return;
    }
    setSuccess(data.instruction);
    onUpdate();
  };

  const markSent = () => {
    const ok = window.confirm(
      `Did you tap SEND on LinkedIn for ${message.name}?`
    );
    if (ok) patchMessage({ status: "SENT" });
  };

  return (
    <div className="message-card">
      <div className="meta">
        <div>
          <strong>{message.name}</strong>
          <span style={{ color: "#888", marginLeft: "0.5rem" }}>
            {message.company}
          </span>
        </div>
        <span className={statusBadgeClass(message.status)}>{message.status}</span>
      </div>
      <textarea
        className="message-textarea"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        disabled={message.status === "SENT"}
      />
      {error && <p className="message-error">{error}</p>}
      {success && <p className="message-success">{success}</p>}
      <div className="message-actions">
        {message.status !== "SENT" && (
          <>
            <button
              className="btn btn-linkedin"
              onClick={openInLinkedIn}
              disabled={opening || !content.trim()}
            >
              {opening ? "Opening LinkedIn..." : "Open in LinkedIn"}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => patchMessage({ content })}
              disabled={saving}
            >
              Save Edit
            </button>
            <button className="btn btn-primary" onClick={markSent}>
              I Tapped Send on LinkedIn
            </button>
          </>
        )}
        {message.status === "SENT" && (
          <span className="badge badge-sent">Sent</span>
        )}
      </div>
      {message.status !== "SENT" && (
        <p className="message-hint">
          Click <strong>Open in LinkedIn</strong> → message appears in LinkedIn → you tap <strong>Send</strong>
        </p>
      )}
    </div>
  );
}

function ConnectionTable({
  connections,
  onStatusChange,
}: {
  connections: Connection[];
  onStatusChange: (id: number, status: string) => void;
}) {
  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Company</th>
          <th>Role</th>
          <th>Score</th>
          <th>Signals</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {connections.map((c) => {
          const breakdown = parseJson<Record<string, number>>(c.score_breakdown) || {};
          const alumni = parseJson<string[]>(c.alumni_tags) || [];
          const job = parseJson<{ company: string; title: string }>(c.job_match);

          return (
            <tr key={c.id}>
              <td>
                <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer">
                  {c.name}
                </a>
              </td>
              <td>{c.company || "—"}</td>
              <td>{c.role || "—"}</td>
              <td>
                <span className={scoreBadgeClass(c.referral_score)}>
                  {c.referral_score ?? "—"}
                </span>
                {Object.keys(breakdown).length > 0 && (
                  <div className="score-breakdown">
                    {Object.entries(breakdown)
                      .map(([k, v]) => `${k} +${v}`)
                      .join(" · ")}
                  </div>
                )}
              </td>
              <td>
                <div className="score-breakdown">
                  {c.recruiter_type && <div>Recruiter: {c.recruiter_type}</div>}
                  {alumni.length > 0 && <div>Alumni: {alumni.join(", ")}</div>}
                  {job && (
                    <div>
                      Job: {job.title} @ {job.company}
                    </div>
                  )}
                </div>
              </td>
              <td>
                <select
                  className="status-select"
                  value={c.outreach_status}
                  onChange={(e) => onStatusChange(c.id, e.target.value)}
                >
                  {OUTREACH_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default function Dashboard() {
  const [tab, setTab] = useState<"top" | "connections" | "messages">("messages");
  const [connections, setConnections] = useState<Connection[]>([]);
  const [topPicks, setTopPicks] = useState<Connection[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [safetyPolicy, setSafetyPolicy] = useState<string>("");

  const loadData = useCallback(async () => {
    try {
      const [connRes, topRes, msgRes, statsRes, safetyRes] = await Promise.all([
        fetch("/api/connections"),
        fetch("/api/connections?top=1"),
        fetch("/api/messages"),
        fetch("/api/stats"),
        fetch("/api/safety"),
      ]);

      if (!connRes.ok || !topRes.ok || !msgRes.ok || !statsRes.ok) {
        throw new Error("Failed to load dashboard data. Is the database initialized?");
      }

      setConnections(await connRes.json());
      setTopPicks(await topRes.json());
      setMessages(await msgRes.json());
      setStats(await statsRes.json());
      const safety = await safetyRes.json();
      setSafetyPolicy(safety.policy || "");
      setError(null);
    } catch (err) {
      setError(String(err));
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const updateStatus = async (connectionId: number, status: string) => {
    await fetch("/api/outreach", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ connectionId, status }),
    });
    loadData();
  };

  const draftCount = messages.filter((m) => m.status === "DRAFT").length;

  return (
    <div className="container">
      <header className="header">
        <h1>LinkedIn Networking Copilot</h1>
        <p>We draft the message in LinkedIn. You tap Send — that is your approval.</p>
      </header>

      <div className="safety-banner">
        <strong>How it works:</strong> Open in LinkedIn → message is pre-filled → you tap <strong>Send</strong> on LinkedIn. We never auto-send.
      </div>

      {error && (
        <div className="section error-banner">
          <p>{error}</p>
          <p className="hint">
            Run <code>python copilot.py seed</code> to populate sample data.
          </p>
        </div>
      )}

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="label">Total Connections</div>
            <div className="value">{stats.total_connections}</div>
          </div>
          <div className="stat-card">
            <div className="label">Contacted</div>
            <div className="value">{stats.contacted}</div>
          </div>
          <div className="stat-card">
            <div className="label">Replied</div>
            <div className="value">{stats.replied}</div>
          </div>
          <div className="stat-card">
            <div className="label">Referral Rate</div>
            <div className="value">{stats.referral_rate}%</div>
          </div>
        </div>
      )}

      <div className="tabs">
        <button
          className={`tab ${tab === "top" ? "active" : ""}`}
          onClick={() => setTab("top")}
        >
          Top Picks ({topPicks.length})
        </button>
        <button
          className={`tab ${tab === "connections" ? "active" : ""}`}
          onClick={() => setTab("connections")}
        >
          All Connections
        </button>
        <button
          className={`tab ${tab === "messages" ? "active" : ""}`}
          onClick={() => setTab("messages")}
        >
          Messages ({draftCount} drafts)
        </button>
      </div>

      {tab === "top" && (
        <div className="section">
          <h2>This Week&apos;s Top Picks</h2>
          {topPicks.length === 0 ? (
            <div className="empty-state">Run analysis to rank your network.</div>
          ) : (
            <ConnectionTable connections={topPicks} onStatusChange={updateStatus} />
          )}
        </div>
      )}

      {tab === "connections" && (
        <div className="section">
          <h2>All Connections</h2>
          {connections.length === 0 ? (
            <div className="empty-state">Run the scraper to collect profiles.</div>
          ) : (
            <ConnectionTable connections={connections} onStatusChange={updateStatus} />
          )}
        </div>
      )}

      {tab === "messages" && (
        <div className="section">
          <h2>Generated Messages</h2>
          {messages.length === 0 ? (
            <div className="empty-state">
              Run <code>python copilot.py messages</code> to generate drafts.
            </div>
          ) : (
            messages.map((m) => (
              <MessageCard key={m.id} message={m} onUpdate={loadData} />
            ))
          )}
        </div>
      )}
    </div>
  );
}
