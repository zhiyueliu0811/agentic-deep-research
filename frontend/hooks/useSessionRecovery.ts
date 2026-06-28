"use client";

import { useEffect, useRef } from "react";
import * as api from "@/lib/api";

const STORAGE_KEY = "deep_research_thread_id";

export function getStoredThreadId(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(STORAGE_KEY) || "";
}

export function setStoredThreadId(tid: string | null) {
  if (typeof window === "undefined") return;
  if (tid) {
    sessionStorage.setItem(STORAGE_KEY, tid);
  } else {
    sessionStorage.removeItem(STORAGE_KEY);
  }
}

interface RecoveryActions {
  onRecoverReview: (tid: string, query: string, draftPreview: string) => void;
  onRecoverCompleted: (tid: string, query: string, finalReport: string, verification: Record<string, unknown> | null) => void;
  onClearSession: () => void;
}

export function useSessionRecovery(actions: RecoveryActions) {
  const restoredRef = useRef(false);

  useEffect(() => {
    const tid = getStoredThreadId();
    if (!tid || restoredRef.current) return;
    restoredRef.current = true;

    (async () => {
      try {
        const status = await api.getTaskStatus(tid);

        if (status.status === "waiting_review") {
          actions.onRecoverReview(tid, status.query || "", status.draft_report || "");
        } else if (status.status === "completed") {
          const report = await api.getReport(tid);
          actions.onRecoverCompleted(
            tid,
            status.query || "",
            report.final_report || "",
            report.verification as Record<string, unknown> | null
          );
        } else {
          actions.onClearSession();
        }
      } catch {
        actions.onClearSession();
      }
    })();
  }, []);
}
