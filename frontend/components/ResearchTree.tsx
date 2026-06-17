"use client";

import { useEffect, useState } from "react";

interface TreeNode {
  id: string;
  type: string;
  label: string;
  detail: string;
}

interface TreeEdge {
  source: string;
  target: string;
}

interface TraceData {
  nodes: TreeNode[];
  edges: TreeEdge[];
}

const AGENT_COLORS: Record<string, string> = {
  agent: "bg-blue-100 border-blue-400 text-blue-800",
  tool: "bg-green-100 border-green-400 text-green-800",
  quality: "bg-yellow-100 border-yellow-400 text-yellow-800",
};

const AGENT_ICONS: Record<string, string> = {
  agent: "🤖",
  tool: "🔧",
  quality: "⭐",
};

export default function ResearchTree({ threadId }: { threadId: string }) {
  const [trace, setTrace] = useState<TraceData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`http://localhost:8000/api/obs/trace/${threadId}`)
      .then((r) => r.json())
      .then(setTrace)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [threadId]);

  if (loading) {
    return <div className="text-gray-400 text-sm py-4">加载执行轨迹...</div>;
  }

  if (!trace || trace.nodes.length === 0) {
    return (
      <div className="text-gray-400 text-sm py-4">
        暂无执行轨迹数据（完成一次研究后自动记录）
      </div>
    );
  }

  // Build adjacency list
  const childrenMap: Record<string, TreeNode[]> = {};
  for (const edge of trace.edges) {
    if (!childrenMap[edge.source]) childrenMap[edge.source] = [];
    const target = trace.nodes.find((n) => n.id === edge.target);
    if (target) childrenMap[edge.source].push(target);
  }

  const roots = trace.nodes.filter(
    (n) => !trace.edges.some((e) => e.target === n.id)
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <h3 className="text-lg font-bold text-gray-800 mb-4">
        🌳 Agent 执行树
      </h3>
      <div className="space-y-1 pl-2">
        {roots.map((node) => (
          <TreeNodeItem
            key={node.id}
            node={node}
            childrenMap={childrenMap}
            depth={0}
          />
        ))}
      </div>
    </div>
  );
}

function TreeNodeItem({
  node,
  childrenMap,
  depth,
}: {
  node: TreeNode;
  childrenMap: Record<string, TreeNode[]>;
  depth: number;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const children = childrenMap[node.id] || [];
  const hasChildren = children.length > 0;

  const colorClass = AGENT_COLORS[node.type] || AGENT_COLORS.agent;
  const icon = AGENT_ICONS[node.type] || AGENT_ICONS.agent;

  return (
    <div className="select-none">
      <div
        className={`flex items-center gap-2 px-3 py-1.5 rounded-md border ${colorClass} cursor-pointer hover:opacity-80 transition-opacity`}
        style={{ marginLeft: depth * 20 }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren && (
          <span className="text-xs w-3">{expanded ? "▼" : "▶"}</span>
        )}
        {!hasChildren && <span className="w-3" />}
        <span>{icon}</span>
        <span className="font-medium text-sm">{node.label}</span>
        {node.detail && (
          <span className="text-xs opacity-60 truncate max-w-[200px]">
            — {node.detail}
          </span>
        )}
      </div>
      {expanded &&
        children.map((child) => (
          <TreeNodeItem
            key={child.id}
            node={child}
            childrenMap={childrenMap}
            depth={depth + 1}
          />
        ))}
    </div>
  );
}
