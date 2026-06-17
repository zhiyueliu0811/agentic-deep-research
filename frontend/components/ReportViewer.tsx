"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  content: string;
  verification?: Record<string, unknown> | null;
}

export default function ReportViewer({ content, verification }: Props) {
  if (!content) {
    return (
      <div className="text-center text-gray-400 py-12">报告尚未生成</div>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto">
      {verification && (
        <VerificationCard verification={verification} />
      )}
      <div className="prose prose-slate max-w-none bg-white rounded-xl shadow-sm border p-8">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content}
        </ReactMarkdown>
      </div>
      <div className="mt-4 flex gap-3 justify-end">
        <button
          onClick={() => {
            const blob = new Blob([content], { type: "text/markdown" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `report_${new Date().toISOString().slice(0, 10)}.md`;
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
        >
          📥 导出 Markdown
        </button>
      </div>
    </div>
  );
}

function VerificationCard({ verification }: { verification: Record<string, unknown> }) {
  const v = verification as Record<string, unknown>;
  const total = (v.total_claims as number) || 0;
  const supported = (v.supported as number) || 0;
  const partial = (v.partial as number) || 0;
  const unsupported = (v.unsupported as number) || 0;
  const hallucinationRate = (v.hallucination_rate as number) || 0;
  const verifiedRate = ((v.verified_rate as number) || (supported + partial) / (total || 1)) * 100;

  const rateColor =
    verifiedRate >= 60 ? "text-green-600" : verifiedRate >= 30 ? "text-amber-500" : "text-red-500";

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
      <h3 className="text-lg font-bold text-gray-800 mb-2">🔬 事实核查结果</h3>
      <p className="text-sm text-gray-500 mb-4">
        对报告中 {total} 条关键断言进行了搜索验证
      </p>

      <div className="grid grid-cols-4 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold text-green-600">{supported}</div>
          <div className="text-xs text-gray-500">已验证 ✓</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-amber-500">{partial}</div>
          <div className="text-xs text-gray-500">部分支持 ~</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-red-500">{unsupported}</div>
          <div className="text-xs text-gray-500">无证据 ✗</div>
        </div>
        <div>
          <div className={`text-2xl font-bold ${rateColor}`}>
            {verifiedRate.toFixed(0)}%
          </div>
          <div className="text-xs text-gray-500">验证通过率</div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t flex justify-between text-sm">
        <span className="text-gray-500">
          验证通过率 = (已验证 + 部分支持) / 总数
        </span>
        <span className="text-gray-400">
          幻觉率: {(hallucinationRate * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}
