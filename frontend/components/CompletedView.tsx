"use client";

import ReportViewer from "@/components/ReportViewer";

interface Props {
  finalReport: string;
  verification: Record<string, unknown> | null;
  onReset: () => void;
}

export default function CompletedView({ finalReport, verification, onReset }: Props) {
  if (!finalReport) {
    return (
      <div className="text-center text-gray-500 py-12">
        研究完成，正在加载报告...
        <br />
        <button onClick={onReset} className="mt-4 text-blue-600 hover:underline">
          返回首页
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ReportViewer content={finalReport} verification={verification} />
      <div className="text-center">
        <button
          onClick={onReset}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          开始新研究
        </button>
      </div>
    </div>
  );
}
