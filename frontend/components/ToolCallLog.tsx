"use client";

import { useEffect, useRef } from "react";

interface ToolCall {
  tool: string;
  input: { type: string; query?: string; topic?: string; reflection?: string };
  timestamp: number;
}

interface Props {
  calls: ToolCall[];
}

export default function ToolCallLog({ calls }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [calls.length]);

  if (calls.length === 0) return null;

  const labelMap: Record<string, string> = {
    search: "🔍 搜索",
    think: "💭 反思",
    research: "🔬 启动研究",
    refine: "✏️ 修正报告",
    complete: "✅ 完成",
  };

  return (
    <div className="w-full max-w-2xl mx-auto mt-6">
      <h3 className="text-lg font-medium text-gray-700 mb-3">
        工具调用日志 ({calls.length})
      </h3>
      <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto font-mono text-sm">
        {calls.map((call, i) => (
          <div key={i} className="text-gray-300 py-0.5 border-b border-gray-800 last:border-0">
            <span className="text-blue-400">{labelMap[call.input?.type] || call.tool}</span>
            {" "}
            <span className="text-gray-500">
              {call.input?.query || call.input?.topic || call.input?.reflection || ""}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
