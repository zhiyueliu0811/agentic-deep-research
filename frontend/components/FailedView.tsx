"use client";

interface Props {
  error: string;
  onReset: () => void;
}

export default function FailedView({ error, onReset }: Props) {
  return (
    <div className="max-w-2xl mx-auto text-center py-12">
      <div className="p-4 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg mb-4">
        {error || "研究任务执行失败"}
      </div>
      <button
        onClick={onReset}
        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
      >
        返回首页
      </button>
    </div>
  );
}
