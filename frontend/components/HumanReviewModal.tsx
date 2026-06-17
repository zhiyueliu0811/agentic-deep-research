"use client";

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
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        <div className="p-6 border-b">
          <h2 className="text-xl font-bold text-gray-800">
            📋 报告草稿审查
          </h2>
          <p className="text-gray-500 mt-1">
            请审查 AI 生成的报告草稿，决定是否继续研究
          </p>
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
            {draftPreview || "草稿内容为空"}
          </div>
        </div>

        <div className="p-6 border-t flex gap-3 justify-end">
          <ReviseButton onSubmit={onRevise} />
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

function ReviseButton({ onSubmit }: { onSubmit: (feedback: string) => void }) {
  const handleClick = () => {
    const feedback = window.prompt("请输入修改意见：");
    if (feedback?.trim()) {
      onSubmit(feedback.trim());
    }
  };

  return (
    <button
      onClick={handleClick}
      className="px-6 py-2.5 bg-amber-500 text-white font-medium rounded-lg hover:bg-amber-600 transition-colors"
    >
      ✎ 修改草稿
    </button>
  );
}
