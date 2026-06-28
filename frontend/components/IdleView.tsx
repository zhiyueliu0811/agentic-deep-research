"use client";

import { useState, useCallback } from "react";
import ResearchForm from "@/components/ResearchForm";
import * as api from "@/lib/api";
import type { TaskListItem } from "@/lib/api";

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

interface Props {
  error: string;
  onSubmit: (query: string) => void;
  onResumeReview: (tid: string, query: string, draftPreview: string) => void;
}

export default function IdleView({ error, onSubmit, onResumeReview }: Props) {
  const [history, setHistory] = useState<TaskListItem[]>([]);

  const loadHistory = useCallback(async () => {
    try {
      const items = await api.getHistory();
      setHistory(items);
    } catch { /* ignore */ }
  }, []);

  return (
    <>
      <ResearchForm onSubmit={onSubmit} />
      {error && (
        <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg max-w-2xl mx-auto">
          {error}
        </div>
      )}
      <div className="mt-8 max-w-2xl mx-auto">
        <button
          onClick={loadHistory}
          className="text-sm text-blue-600 hover:underline mb-2"
        >
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
                      : isStuck
                      ? "opacity-60"
                      : ""
                  }`}
                  onClick={async () => {
                    if (canOpen) {
                      window.open(`/report/${t.thread_id}`, "_blank");
                    } else if (canResume) {
                      const status = await api.getTaskStatus(t.thread_id);
                      onResumeReview(
                        t.thread_id,
                        t.query,
                        status.draft_report || ""
                      );
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
  );
}
