"use client";

import ProgressTimeline from "@/components/ProgressTimeline";
import ToolCallLog from "@/components/ToolCallLog";
import type { ToolCall } from "@/hooks/useResearchState";

interface Props {
  query: string;
  threadId: string;
  currentNode: string;
  completedNodes: string[];
  toolCalls: ToolCall[];
  isResuming: boolean;
}

export default function RunningView({
  query,
  threadId,
  currentNode,
  completedNodes,
  toolCalls,
  isResuming,
}: Props) {
  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-4 max-w-2xl mx-auto">
        <div className="text-sm text-gray-500 dark:text-gray-400">研究主题</div>
        <div className="text-gray-800 dark:text-gray-100 font-medium">{query}</div>
        <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
          Thread: {threadId}
          <span className="ml-2 text-green-600 font-medium">✓ 可安全刷新</span>
          {isResuming && (
            <span className="ml-2 text-blue-600 font-medium">↻ 正在恢复研究...</span>
          )}
        </div>
      </div>
      <ProgressTimeline currentNode={currentNode} completedNodes={completedNodes} />
      <ToolCallLog calls={toolCalls} />
    </div>
  );
}
