"use client";

import { useEffect, useState } from "react";

interface ModelStats {
  input_tokens: number;
  output_tokens: number;
  cost_rmb: number;
  calls: number;
}

interface CostData {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost_rmb: number;
  model_stats: Record<string, ModelStats>;
  records: Array<{
    timestamp: number;
    model: string;
    input_tokens: number;
    output_tokens: number;
    cost_rmb: number;
  }>;
}

export default function CostDashboard({ threadId }: { threadId: string }) {
  const [cost, setCost] = useState<CostData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`http://localhost:8000/api/obs/cost/${threadId}`)
      .then((r) => r.json())
      .then(setCost)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [threadId]);

  if (loading) {
    return <div className="text-gray-400 text-sm py-4">加载成本数据...</div>;
  }

  if (!cost || cost.total_tokens === 0) {
    return (
      <div className="text-gray-400 text-sm py-4">
        暂无 Token 消耗数据
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <h3 className="text-lg font-bold text-gray-800 mb-4">
        📊 Token 消耗 & 成本
      </h3>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard label="总 Token" value={cost.total_tokens.toLocaleString()} />
        <StatCard label="输入 Token" value={cost.total_input_tokens.toLocaleString()} />
        <StatCard label="输出 Token" value={cost.total_output_tokens.toLocaleString()} />
        <StatCard label="总费用 (RMB)" value={`¥${cost.total_cost_rmb.toFixed(4)}`} highlight />
      </div>

      {/* Per-Model Breakdown */}
      {Object.keys(cost.model_stats).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-600 mb-2">各模型明细</h4>
          <div className="space-y-2">
            {Object.entries(cost.model_stats).map(([model, stats]) => (
              <div
                key={model}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div>
                  <div className="text-sm font-medium text-gray-700">{model}</div>
                  <div className="text-xs text-gray-400">
                    {stats.calls} 次调用
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-700">
                    {(stats.input_tokens + stats.output_tokens).toLocaleString()} tokens
                  </div>
                  <div className="text-xs text-amber-600 font-medium">
                    ¥{stats.cost_rmb.toFixed(4)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 text-center">
      <div
        className={`text-lg font-bold ${
          highlight ? "text-amber-600" : "text-gray-800"
        }`}
      >
        {value}
      </div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}
