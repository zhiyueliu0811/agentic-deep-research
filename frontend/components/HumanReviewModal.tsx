"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  draftPreview: string;
  isOpen: boolean;
  onApprove: () => void;
  onRevise: (feedback: string) => void;
}

export default function HumanReviewModal({
  draftPreview,
  isOpen,
  onApprove,
  onRevise,
}: Props) {
  const [showRevise, setShowRevise] = useState(false);
  const [feedback, setFeedback] = useState("");

  if (!isOpen) return null;

  const handleSubmitRevise = () => {
    if (feedback.trim()) {
      onRevise(feedback.trim());
      setFeedback("");
      setShowRevise(false);
    }
  };

  const handleCancelRevise = () => {
    setFeedback("");
    setShowRevise(false);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-4xl w-full max-h-[85vh] flex flex-col">
        <div className="p-6 border-b dark:border-gray-700">
          <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">
            📋 报告草稿审查
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            请审查 AI 生成的报告草稿，决定是否继续研究
          </p>
        </div>

        <div className="p-8 overflow-y-auto flex-1">
          <div className="prose prose-base dark:prose-invert max-w-none text-gray-800 dark:text-gray-200 break-words [&_pre]:overflow-x-auto [&_pre]:whitespace-pre-wrap [&_code]:break-all">
            {draftPreview ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {draftPreview}
              </ReactMarkdown>
            ) : (
              <p className="text-gray-400">草稿内容为空</p>
            )}
          </div>
        </div>

        {showRevise && (
          <div className="px-6 pb-2">
            <textarea
              className="w-full border border-gray-300 rounded-lg p-3 text-sm focus:ring-2 focus:ring-amber-400 focus:border-amber-400 outline-none resize-none"
              rows={3}
              placeholder="请输入修改意见…"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              autoFocus
            />
            <div className="flex gap-2 justify-end mt-2">
              <button
                onClick={handleCancelRevise}
                className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
              >
                取消
              </button>
              <button
                onClick={handleSubmitRevise}
                disabled={!feedback.trim()}
                className="px-4 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-40 transition-colors"
              >
                提交修改意见
              </button>
            </div>
          </div>
        )}

        <div className="p-6 border-t flex gap-3 justify-end">
          <button
            onClick={() => setShowRevise(true)}
            className="px-6 py-2.5 bg-amber-500 text-white font-medium rounded-lg hover:bg-amber-600 transition-colors"
          >
            ✎ 修改草稿
          </button>
          <button
            onClick={onApprove}
            className="px-6 py-2.5 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors"
          >
            ✓ 批准，继续研究
          </button>
        </div>
      </div>
    </div>
  );
}
