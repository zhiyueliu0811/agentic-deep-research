"use client";

import { useReducer, useCallback } from "react";

// ---- State Machine ----
// 明确定义所有合法状态和转移，防止"不可能状态"

export type AppState =
  | "idle"
  | "running"
  | "review"
  | "resuming"
  | "completed"
  | "failed";

export interface ToolCall {
  tool: string;
  input: { type: string; query?: string; topic?: string; reflection?: string };
  timestamp: number;
}

export interface ResearchState {
  appState: AppState;
  threadId: string;
  query: string;
  currentNode: string;
  completedNodes: string[];
  toolCalls: ToolCall[];
  draftPreview: string;
  finalReport: string;
  verification: Record<string, unknown> | null;
  error: string;
}

const initialState: ResearchState = {
  appState: "idle",
  threadId: "",
  query: "",
  currentNode: "",
  completedNodes: [],
  toolCalls: [],
  draftPreview: "",
  finalReport: "",
  verification: null,
  error: "",
};

// ---- Actions ----
type Action =
  | { type: "START_RESEARCH"; threadId: string; query: string }
  | { type: "SET_RUNNING" }
  | { type: "SET_REVIEW"; draftPreview: string }
  | { type: "SET_RESUMING" }
  | { type: "SET_COMPLETED"; finalReport: string; verification: Record<string, unknown> | null }
  | { type: "SET_FAILED"; error: string }
  | { type: "SET_NODE_START"; node: string }
  | { type: "SET_NODE_COMPLETE"; node: string }
  | { type: "ADD_TOOL_CALL"; tool: string; input: ToolCall["input"] }
  | { type: "RECOVER_REVIEW"; threadId: string; query: string; draftPreview: string }
  | { type: "RECOVER_COMPLETED"; threadId: string; query: string; finalReport: string; verification: Record<string, unknown> | null }
  | { type: "RESET" }
  | { type: "SET_STREAM_ERROR"; error: string };

function reducer(state: ResearchState, action: Action): ResearchState {
  switch (action.type) {
    case "START_RESEARCH":
      return {
        ...initialState,
        appState: "running",
        threadId: action.threadId,
        query: action.query,
      };

    case "SET_RUNNING":
      return { ...state, appState: "running" };

    case "SET_REVIEW":
      return {
        ...state,
        appState: "review",
        draftPreview: action.draftPreview,
      };

    case "SET_RESUMING":
      return {
        ...state,
        appState: "resuming",
        draftPreview: "",
        completedNodes: [],
        toolCalls: [],
        currentNode: "",
      };

    case "SET_COMPLETED":
      return {
        ...state,
        appState: "completed",
        finalReport: action.finalReport,
        verification: action.verification,
      };

    case "SET_FAILED":
      return {
        ...state,
        appState: "failed",
        error: action.error,
      };

    case "SET_NODE_START":
      return { ...state, currentNode: action.node };

    case "SET_NODE_COMPLETE":
      return {
        ...state,
        completedNodes: state.completedNodes.includes(action.node)
          ? state.completedNodes
          : [...state.completedNodes, action.node],
      };

    case "ADD_TOOL_CALL":
      return {
        ...state,
        toolCalls: [
          ...state.toolCalls,
          { tool: action.tool, input: action.input, timestamp: Date.now() },
        ],
      };

    case "RECOVER_REVIEW":
      return {
        ...initialState,
        appState: "review",
        threadId: action.threadId,
        query: action.query,
        draftPreview: action.draftPreview,
      };

    case "RECOVER_COMPLETED":
      return {
        ...initialState,
        appState: "completed",
        threadId: action.threadId,
        query: action.query,
        finalReport: action.finalReport,
        verification: action.verification,
      };

    case "RESET":
      return initialState;

    case "SET_STREAM_ERROR":
      return {
        ...state,
        appState: "failed",
        error: action.error,
      };

    default:
      return state;
  }
}

export function useResearchState() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const reset = useCallback(() => dispatch({ type: "RESET" }), []);

  return { state, dispatch, reset };
}
