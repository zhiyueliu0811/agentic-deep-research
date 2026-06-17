"use client";

const STAGES = [
  { node: "write_research_brief", label: "研究简报", icon: "📋" },
  { node: "write_draft_report", label: "草稿生成", icon: "📝" },
  { node: "human_review", label: "人工审查", icon: "👀" },
  { node: "supervisor", label: "任务调度", icon: "🎯" },
  { node: "supervisor_tools", label: "并行研究", icon: "⚡" },
  { node: "red_team", label: "红队审查", icon: "🛡️" },
  { node: "claim_verification", label: "事实核查", icon: "✅" },
  { node: "final_report_generation", label: "最终报告", icon: "📄" },
];

interface Props {
  currentNode: string;
  completedNodes: string[];
}

export default function ProgressTimeline({ currentNode, completedNodes }: Props) {
  return (
    <div className="w-full max-w-2xl mx-auto">
      <h3 className="text-lg font-medium text-gray-700 mb-4">研究进度</h3>
      <div className="space-y-2">
        {STAGES.map((stage, i) => {
          const isCompleted = completedNodes.includes(stage.node);
          const isActive = currentNode === stage.node;
          const isPending = !isCompleted && !isActive;

          return (
            <div
              key={stage.node}
              className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${
                isActive
                  ? "bg-blue-100 border border-blue-300 animate-pulse"
                  : isCompleted
                  ? "bg-green-50 border border-green-200"
                  : "bg-gray-50 border border-gray-100"
              }`}
            >
              <span className="text-xl">{stage.icon}</span>
              <span
                className={`flex-1 font-medium ${
                  isActive
                    ? "text-blue-700"
                    : isCompleted
                    ? "text-green-700"
                    : "text-gray-400"
                }`}
              >
                {stage.label}
              </span>
              {isCompleted && (
                <span className="text-green-500 text-sm font-bold">✓</span>
              )}
              {isActive && (
                <span className="flex gap-0.5">
                  <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" />
                  <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
                  <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
