const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

export interface TaskCreated {
  thread_id: string;
  status: string;
  created_at: string;
}

export interface TaskStatus {
  thread_id: string;
  status: string;
  stage: string;
  query: string;
  draft_report: string;
  final_report: string;
  verification: unknown;
  error: string;
}

export interface TaskListItem {
  thread_id: string;
  query: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ReportData {
  thread_id: string;
  query: string;
  final_report: string;
  verification: unknown;
  draft_report: string;
}

export async function startResearch(query: string): Promise<TaskCreated> {
  const res = await fetch(`${API_BASE}/research/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error("Failed to start research");
  return res.json();
}

export async function getTaskStatus(threadId: string): Promise<TaskStatus> {
  const res = await fetch(`${API_BASE}/research/${threadId}/status`);
  if (!res.ok) throw new Error("Task not found");
  return res.json();
}

export async function getReport(threadId: string): Promise<ReportData> {
  const res = await fetch(`${API_BASE}/research/${threadId}/report`);
  if (!res.ok) throw new Error("Report not found");
  return res.json();
}

export async function getHistory(): Promise<TaskListItem[]> {
  const res = await fetch(`${API_BASE}/research/history/list`);
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}

export function getStreamUrl(threadId: string): string {
  return `${API_BASE}/research/${threadId}/stream`;
}

export function getResumeUrl(threadId: string): string {
  return `${API_BASE}/research/${threadId}/resume`;
}

export async function deleteTask(threadId: string): Promise<void> {
  await fetch(`${API_BASE}/research/${threadId}`, { method: "DELETE" });
}
