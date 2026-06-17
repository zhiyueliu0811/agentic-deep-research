"use client";

import { useState } from "react";

interface Props {
  onSubmit: (query: string) => void;
  disabled?: boolean;
}

export default function ResearchForm({ onSubmit, disabled }: Props) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !disabled) {
      onSubmit(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="flex flex-col gap-4">
        <label className="text-lg font-medium text-gray-700">
          输入你的研究主题
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="例如：请研究 2025 年 AI Agent 框架的发展趋势"
          rows={4}
          disabled={disabled}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:bg-gray-100"
        />
        <button
          type="submit"
          disabled={disabled || !query.trim()}
          className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {disabled ? "研究中..." : "开始研究"}
        </button>
      </div>
    </form>
  );
}
