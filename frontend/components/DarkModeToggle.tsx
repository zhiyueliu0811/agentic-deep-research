"use client";

import { useState, useEffect } from "react";

export default function DarkModeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    setDark(isDark);
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  // 页面加载时从 localStorage 恢复
  useEffect(() => {
    const saved = localStorage.getItem("theme");
    if (saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
      document.documentElement.classList.add("dark");
      setDark(true);
    }
  }, []);

  return (
    <button
      onClick={toggle}
      className="fixed top-4 right-4 z-50 p-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all"
      aria-label={dark ? "切换到亮色模式" : "切换到暗色模式"}
      title={dark ? "切换到亮色模式" : "切换到暗色模式"}
    >
      {dark ? "☀️" : "🌙"}
    </button>
  );
}
