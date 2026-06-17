"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import ResearchForm from "@/components/ResearchForm";
import ProgressTimeline from "@/components/ProgressTimeline";
import ToolCallLog from "@/components/ToolCallLog";
import HumanReviewModal from "@/components/HumanReviewModal";
import ReportViewer from "@/components/ReportViewer";
import * as api from "@/lib/api";
import type { SSEEvent } from "@/lib/useSSE";

const STATUS_LABELS: Record<string, string> = {
  pending: "等待中",
  running: "研究中",
  waiting_review: "待审查",
  completed: "已完成",
  failed: "失败",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  running: "bg-blue-100 text-blue-700",
  waiting_review: "bg-yellow-100 text-yellow-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

type AppState = "idle" | "running" | "review" | "resuming" | "completed" | "failed";

interface ToolCall {
  tool: string;
  input: { type: string; query?: string; topic?: string; reflection?: string };
  timestamp: number;
}

const STORAGE_KEY = "deep_research_thread_id";

function getStoredThreadId(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(STORAGE_KEY) || "";
}

function setStoredThreadId(tid: string | null) {
  if (typeof window === "undefined") return;
  if (tid) {
    sessionStorage.setItem(STORAGE_KEY, tid);
  } else {
    sessionStorage.removeItem(STORAGE_KEY);
  }
}

export default function HomePage() {
  const [appState, setAppState] = useState<AppState>("idle");
  const [threadId, setThreadId] = useState<string>(() => getStoredThreadId());
  const [query, setQuery] = useState("");
  const [currentNode, setCurrentNode] = useState("");
  const [completedNodes, setCompletedNodes] = useState<string[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [draftPreview, setDraftPreview] = useState("");
  const [finalReport, setFinalReport] = useState("");
  const [verification, setVerification] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<api.TaskListItem[]>([]);

  const eventSourceRef = useRef<EventSource | null>(null);
  const restoredRef = useRef(false);

  // 页面首次加载时，从 sessionStorage 恢复任务状态
  useEffect(() => {
    const tid = getStoredThreadId();
    if (!tid || restoredRef.current) return;
    restoredRef.current = true;
    (async () => {
      try {
        const status = await api.getTaskStatus(tid);
        setQuery(status.query || "");
        setThreadId(tid);

        if (status.status === "waiting_review") {
          setDraftPreview(status.draft_report?.slice(0, 2000) || "");
          setAppState("review");
        } else if (status.status === "completed") {
          const report = await api.getReport(tid);
          setFinalReport(report.final_report || "");
          setVerification(report.verification as Record<string, unknown> | null);
          setAppState("completed");
        } else {
          // 失败/进行中/未知：清理
          setStoredThreadId(null);
          setThreadId("");
          setAppState("idle");
        }
      } catch {
        setStoredThreadId(null);
        setThreadId("");
        setAppState("idle");
      }
    })();
  }, []);

  const closeSSE = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  const connectSSE = useCallback(
    (url: string, tid: string) => {
      closeSSE();
      const es = new EventSource(url);

      es.onmessage = async (e) => {
        try {
          const { event, data } = JSON.parse(e.data) as SSEEvent;

          switch (event) {
            case "node_start":
              setCurrentNode(data.node as string);
              break;
            case "node_complete":
              setCompletedNodes((prev) => {
                if (prev.includes(data.node as string)) return prev;
                return [...prev, data.node as string];
              });
              break;
            case "tool_call":
              setToolCalls((prev) => [
                ...prev,
                { tool: data.tool as string, input: data.input as ToolCall["input"], timestamp: Date.now() },
              ]);
              break;
            case "human_review_required":
              setAppState("review");
              setDraftPreview((data.draft_preview as string) || (data.message as string) || "");
              closeSSE();
              break;
            case "complete": {
              closeSSE();
              if (!tid) {
                setAppState("idle");
                return;
              }
              try {
                const report = await api.getReport(tid);
                setFinalReport(report.final_report || "");
                setVerification(report.verification as Record<string, unknown> | null);
                setAppState("completed");
              } catch {
                setError("任务完成，但最终报告加载失败");
                setAppState("idle");
              }
              break;
            }
            case "error":
              closeSSE();
              setError((data.message as string) || "研究任务执行失败");
              setAppState("failed");
              break;
          }
        } catch { /* ignore */ }
      };

      es.onerror = async () => {
        es.close();
        if (tid) {
          try {
            const status = await api.getTaskStatus(tid);
            if (status.status === "waiting_review") {
              setAppState("review");
              setDraftPreview(status.draft_report?.slice(0, 2000) || "");
              return;
            }
            if (status.status === "completed") {
              setAppState("completed");
              const report = await api.getReport(tid);
              setFinalReport(report.final_report || "");
              setVerification(report.verification as Record<string, unknown> | null);
              return;
            }
          } catch { /* ignore */ }
        }
      };

      eventSourceRef.current = es;
    },
    [closeSSE]
  );

  const handleSubmit = useCallback(
    async (q: string) => {
      setQuery(q);
      setError("");
      setToolCalls([]);
      setCompletedNodes([]);
      setCurrentNode("");
      setFinalReport("");
      setVerification(null);
      setDraftPreview("");

      try {
        const { thread_id } = await api.startResearch(q);
        setThreadId(thread_id);
        setStoredThreadId(thread_id);
        setAppState("running");
        connectSSE(api.getStreamUrl(thread_id), thread_id);
      } catch {
        setError("启动研究任务失败，请确认后端已启动");
        setAppState("idle");
      }
    },
    [connectSSE]
  );

  const handleApprove = useCallback(async () => {
    if (!threadId) return;
    setAppState("resuming");
    setDraftPreview("");
    closeSSE();
    await fetch(api.getResumeUrl(threadId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "approve", feedback: "" }),
    });
    setToolCalls([]);
    setCompletedNodes([]);
    setCurrentNode("");
    connectSSE(api.getStreamUrl(threadId), threadId);
  }, [threadId, closeSSE, connectSSE]);

  const handleRevise = useCallback(
    async (feedback: string) => {
      if (!threadId) return;
      setAppState("resuming");
      setDraftPreview("");
      closeSSE();
      await fetch(api.getResumeUrl(threadId), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "revise", feedback }),
      });
      setToolCalls([]);
      setCompletedNodes([]);
      setCurrentNode("");
      connectSSE(api.getStreamUrl(threadId), threadId);
    },
    [threadId, closeSSE, connectSSE]
  );

  const handleReset = useCallback(() => {
    closeSSE();
    setStoredThreadId(null);
    setAppState("idle");
    setThreadId("");
    setQuery("");
    setCurrentNode("");
    setCompletedNodes([]);
    setToolCalls([]);
    setDraftPreview("");
    setFinalReport("");
    setVerification(null);
    setError("");
  }, [closeSSE]);

  const loadHistory = useCallback(async () => {
    try {
      const items = await api.getHistory();
      setHistory(items);
    } catch { /* ignore */ }
  }, []);

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold text-center text-gray-900 mb-2">
          Agentic Deep Research Platform
        </h1>
        <p className="text-center text-gray-500 mb-8">
          基于 LangGraph 的多智能体深度研究系统
        </p>

        {/* Idle: Research Form */}
        {appState === "idle" && !finalReport && (
          <>
            <ResearchForm onSubmit={handleSubmit} />
            {error && (
              <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg max-w-2xl mx-auto">{error}</div>
            )}
            <div className="mt-8 max-w-2xl mx-auto">
              <button onClick={loadHistory} className="text-sm text-blue-600 hover:underline mb-2">
                查看历史任务
              </button>
              {history.length > 0 && (
                <div className="space-y-2 mt-2">
                  {history.map((t) => {
                    const canOpen = t.status === "completed" || t.status === "failed";
                    const canResume = t.status === "waiting_review";
                    const isStuck = t.status === "pending" || t.status === "running";
                    return (
                      <div
                        key={t.thread_id}
                        className={`flex items-center justify-between p-3 bg-white rounded-lg border ${
                          canOpen || canResume
                            ? "cursor-pointer hover:shadow-md hover:border-blue-300 transition-all"
                            : isStuck ? "opacity-60" : ""
                        }`}
                        onClick={async () => {
                          if (canOpen) {
                            window.open(`/report/${t.thread_id}`, "_blank");
                          } else if (canResume) {
                            setThreadId(t.thread_id);
                            setStoredThreadId(t.thread_id);
                            setQuery(t.query);
                            const status = await api.getTaskStatus(t.thread_id);
                            setDraftPreview(status.draft_report?.slice(0, 2000) || "");
                            setAppState("review");
                          }
                        }}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-gray-700 truncate max-w-md">
                            {t.query || "（无标题）"}
                          </div>
                          <div className="text-xs text-gray-400">
                            {t.created_at}
                            {isStuck && " · 任务未完成"}
                          </div>
                        </div>
                        <span className={`text-xs px-2 py-1 rounded-full ml-3 shrink-0 ${STATUS_COLORS[t.status] || "bg-gray-100 text-gray-600"}`}>
                          {STATUS_LABELS[t.status] || t.status}
                        </span>
                        {canOpen && <span className="text-gray-400 ml-2 text-sm">→</span>}
                        {canResume && <span className="text-blue-500 ml-2 text-xs font-medium">点击审查 →</span>}
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            await api.deleteTask(t.thread_id);
                            loadHistory();
                          }}
                          className="ml-2 text-xs text-red-400 hover:text-red-600 shrink-0"
                          title="删除"
                        >
                          ✕
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}

        {/* Running / Resuming: Progress View */}
        {(appState === "running" || appState === "resuming") && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border p-4 max-w-2xl mx-auto">
              <div className="text-sm text-gray-500">研究主题</div>
              <div className="text-gray-800 font-medium">{query}</div>
              <div className="text-xs text-gray-400 mt-1">
                Thread: {threadId}
                <span className="ml-2 text-green-600 font-medium">✓ 可安全刷新</span>
              </div>
            </div>
            <ProgressTimeline currentNode={currentNode} completedNodes={completedNodes} />
            <ToolCallLog calls={toolCalls} />
          </div>
        )}

        {/* Review Modal */}
        <HumanReviewModal
          draftPreview={draftPreview}
          isOpen={appState === "review"}
          onApprove={handleApprove}
          onRevise={handleRevise}
        />

        {/* Failed: Error State */}
        {appState === "failed" && (
          <div className="max-w-2xl mx-auto text-center py-12">
            <div className="p-4 bg-red-50 text-red-700 rounded-lg mb-4">{error || "研究任务执行失败"}</div>
            <button
              onClick={handleReset}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              返回首页
            </button>
          </div>
        )}

        {/* Completed: Final Report */}
        {appState === "completed" && (
          <div className="space-y-6">
            {finalReport ? (
              <>
                <ReportViewer content={finalReport} verification={verification} />
                <div className="text-center">
                  <button
                    onClick={handleReset}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    开始新研究
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center text-gray-500 py-12">
                研究完成，正在加载报告...
                <br />
                <button onClick={handleReset} className="mt-4 text-blue-600 hover:underline">返回首页</button>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
