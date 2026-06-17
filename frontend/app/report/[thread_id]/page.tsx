"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import ReportViewer from "@/components/ReportViewer";
import ResearchTree from "@/components/ResearchTree";
import CostDashboard from "@/components/CostDashboard";
import * as api from "@/lib/api";

type Tab = "report" | "trace" | "cost";

export default function ReportPage({
  params,
}: {
  params: Promise<{ thread_id: string }>;
}) {
  const { thread_id } = use(params);
  const [report, setReport] = useState<api.ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("report");

  useEffect(() => {
    api
      .getReport(thread_id)
      .then(setReport)
      .catch(() => setError("报告未找到或任务尚未完成"))
      .finally(() => setLoading(false));
  }, [thread_id]);

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500 animate-pulse">加载中...</div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-lg mb-4">{error}</div>
          <Link href="/" className="text-blue-600 hover:underline">
            返回首页
          </Link>
        </div>
      </main>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "report", label: "📄 报告" },
    { key: "trace", label: "🌳 执行轨迹" },
    { key: "cost", label: "📊 成本分析" },
  ];

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">研究报告</h1>
            {report?.query && (
              <p className="text-gray-500 mt-1">{report.query}</p>
            )}
          </div>
          <Link href="/" className="text-sm text-blue-600 hover:underline">
            ← 返回首页
          </Link>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                activeTab === tab.key
                  ? "bg-white text-blue-600 border border-b-white -mb-px"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === "report" && (
          <ReportViewer
            content={report?.final_report || ""}
            verification={report?.verification as Record<string, unknown> | null}
          />
        )}
        {activeTab === "trace" && <ResearchTree threadId={thread_id} />}
        {activeTab === "cost" && <CostDashboard threadId={thread_id} />}
      </div>
    </main>
  );
}
