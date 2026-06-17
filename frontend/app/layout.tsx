import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agentic Deep Research Platform",
  description: "基于 LangGraph 的多智能体深度研究系统",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
