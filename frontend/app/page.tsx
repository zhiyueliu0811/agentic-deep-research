"use client";

import { useRef, useCallback, useEffect } from "react";
import IdleView from "@/components/IdleView";
import RunningView from "@/components/RunningView";
import HumanReviewModal from "@/components/HumanReviewModal";
import CompletedView from "@/components/CompletedView";
import FailedView from "@/components/FailedView";
import ErrorBoundary from "@/components/ErrorBoundary";
import DarkModeToggle from "@/components/DarkModeToggle";
import * as api from "@/lib/api";
import type { SSEEvent } from "@/lib/useSSE";
import { useResearchState } from "@/hooks/useResearchState";
import {
  useSessionRecovery,
  setStoredThreadId,
} from "@/hooks/useSessionRecovery";
import type { ToolCall } from "@/hooks/useResearchState";

export default function HomePage() {
  const { state, dispatch, reset } = useResearchState();
  const eventSourceRef = useRef<EventSource | null>(null);
  const threadIdRef = useRef<string>("");

  // 始终保持 ref 和 state 同步，避免闭包陷阱
  useEffect(() => {
    threadIdRef.current = state.threadId;
  }, [state.threadId]);

  // Session recovery on first load
  useSessionRecovery({
    onRecoverReview: (tid, query, draftPreview) => {
      dispatch({ type: "RECOVER_REVIEW", threadId: tid, query, draftPreview });
    },
    onRecoverCompleted: (tid, query, finalReport, verification) => {
      dispatch({
        type: "RECOVER_COMPLETED",
        threadId: tid,
        query,
        finalReport,
        verification,
      });
    },
    onClearSession: () => {
      setStoredThreadId(null);
    },
  });

  // ---- SSE Helpers ----
  const closeSSE = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  const connectSSE = useCallback(
    (url: string, tid: string) => {
      closeSSE();

      let retryCount = 0;

      const doConnect = () => {
        const es = new EventSource(url);
        eventSourceRef.current = es;

        es.onmessage = async (e) => {
          retryCount = 0;
          try {
            const { event, data } = JSON.parse(e.data) as SSEEvent;

            switch (event) {
              case "node_start":
                dispatch({ type: "SET_NODE_START", node: data.node as string });
                break;
              case "node_complete":
                dispatch({
                  type: "SET_NODE_COMPLETE",
                  node: data.node as string,
                });
                break;
              case "tool_call":
                dispatch({
                  type: "ADD_TOOL_CALL",
                  tool: data.tool as string,
                  input: data.input as ToolCall["input"],
                });
                break;
              case "report_chunk":
                // 流式渲染：累加到 finalReport
                // handled by parent via progressive rendering
                break;
              case "human_review_required":
                dispatch({
                  type: "SET_REVIEW",
                  draftPreview:
                    (data.draft_preview as string) || (data.message as string) || "",
                });
                closeSSE();
                break;
              case "complete": {
                closeSSE();
                if (!tid) {
                  reset();
                  return;
                }
                try {
                  const report = await api.getReport(tid);
                  dispatch({
                    type: "SET_COMPLETED",
                    finalReport: report.final_report || "",
                    verification:
                      report.verification as Record<string, unknown> | null,
                  });
                } catch {
                  dispatch({
                    type: "SET_FAILED",
                    error: "任务完成，但最终报告加载失败",
                  });
                }
                break;
              }
              case "error":
                closeSSE();
                dispatch({
                  type: "SET_FAILED",
                  error: (data.message as string) || "研究任务执行失败",
                });
                break;
            }
          } catch { /* ignore malformed events */ }
        };

        es.onerror = async () => {
          es.close();
          const delay = Math.min(1000 * 2 ** retryCount, 30000);
          retryCount++;
          console.log(
            `SSE 连接断开，${delay / 1000}s 后第 ${retryCount} 次重连...`
          );
          await new Promise((resolve) => setTimeout(resolve, delay));
          doConnect();
        };
      };

      doConnect();
    },
    [closeSSE, dispatch, reset]
  );

  // ---- Handlers ----
  const handleSubmit = useCallback(
    async (q: string) => {
      console.log("[DEBUG] handleSubmit called with:", q);
      try {
        const url = api.getStreamUrl("__health_check__");
        console.log("[DEBUG] API_BASE check:", url);
        const { thread_id } = await api.startResearch(q);
        console.log("[DEBUG] startResearch OK, thread_id:", thread_id);
        setStoredThreadId(thread_id);
        dispatch({ type: "START_RESEARCH", threadId: thread_id, query: q });
        connectSSE(api.getStreamUrl(thread_id), thread_id);
      } catch (err) {
        console.error("[DEBUG] startResearch failed:", err);
        dispatch({
          type: "SET_FAILED",
          error: "启动研究任务失败，请确认后端已启动",
        });
      }
    },
    [connectSSE, dispatch]
  );

  const handleApprove = useCallback(async () => {
    const tid = threadIdRef.current;
    if (!tid) return;
    dispatch({ type: "SET_RESUMING" });
    closeSSE();
    try {
      await fetch(api.getResumeUrl(tid), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "approve", feedback: "" }),
      });
      connectSSE(api.getStreamUrl(tid), tid);
    } catch (err) {
      console.error("handleApprove fetch failed:", err);
      dispatch({ type: "SET_FAILED", error: "网络请求失败，请确认后端已启动" });
    }
  }, [closeSSE, connectSSE, dispatch]);

  const handleRevise = useCallback(
    async (feedback: string) => {
      const tid = threadIdRef.current;
      if (!tid) return;
      dispatch({ type: "SET_RESUMING" });
      closeSSE();
      try {
        await fetch(api.getResumeUrl(tid), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "revise", feedback }),
        });
        connectSSE(api.getStreamUrl(tid), tid);
      } catch (err) {
        console.error("handleRevise fetch failed:", err);
        dispatch({ type: "SET_FAILED", error: "网络请求失败，请确认后端已启动" });
      }
    },
    [closeSSE, connectSSE, dispatch]
  );

  const handleReset = useCallback(() => {
    closeSSE();
    setStoredThreadId(null);
    reset();
  }, [closeSSE, reset]);

  const handleResumeReview = useCallback(
    (tid: string, query: string, draftPreview: string) => {
      setStoredThreadId(tid);
      dispatch({
        type: "RECOVER_REVIEW",
        threadId: tid,
        query,
        draftPreview,
      });
    },
    [dispatch]
  );

  // ---- Render ----
  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      <DarkModeToggle />
      <ErrorBoundary>
        <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12">
          <h1 className="text-2xl sm:text-3xl font-bold text-center text-gray-900 dark:text-gray-100 mb-2">
            Agentic Deep Research Platform
          </h1>
          <p className="text-center text-gray-500 dark:text-gray-400 mb-6 sm:mb-8 text-sm sm:text-base">
            基于 LangGraph 的多智能体深度研究系统
          </p>

          {/* Idle: Research Form + History */}
          {state.appState === "idle" && !state.finalReport && (
            <IdleView
              error={state.error}
              onSubmit={handleSubmit}
              onResumeReview={handleResumeReview}
            />
          )}

          {/* Running / Resuming: Progress View */}
          {(state.appState === "running" || state.appState === "resuming") && (
            <RunningView
              query={state.query}
              threadId={state.threadId}
              currentNode={state.currentNode}
              completedNodes={state.completedNodes}
              toolCalls={state.toolCalls}
              isResuming={state.appState === "resuming"}
            />
          )}

          {/* Review Modal */}
          <HumanReviewModal
            draftPreview={state.draftPreview}
            isOpen={state.appState === "review"}
            onApprove={handleApprove}
            onRevise={handleRevise}
          />

          {/* Failed */}
          {state.appState === "failed" && (
            <FailedView error={state.error} onReset={handleReset} />
          )}

          {/* Completed */}
          {state.appState === "completed" && (
            <CompletedView
              finalReport={state.finalReport}
              verification={state.verification}
              onReset={handleReset}
            />
          )}
        </div>
      </ErrorBoundary>
    </main>
  );
}
