# Deep Research Frontend

基于 Next.js 15 的深度研究平台前端，支持 SSE 实时进度推送和 HITL 人工审查。

## 技术栈

- **框架**: Next.js 15 (App Router)
- **语言**: TypeScript
- **样式**: CSS Modules + Global CSS
- **数据交互**: SSE (Server-Sent Events) + REST API

## 组件结构

```
components/
├── ResearchForm.tsx       # 研究查询输入
├── ProgressTimeline.tsx   # SSE 实时进度时间线
├── ResearchTree.tsx       # Agent 执行树状图
├── ReportViewer.tsx       # 最终报告渲染
├── HumanReviewModal.tsx   # HITL 审查弹窗
├── CostDashboard.tsx      # Token 成本面板
└── ToolCallLog.tsx        # 工具调用日志
```

## 启动

```bash
npm install
npm run dev
```

浏览器打开 `http://localhost:3000`，确保后端已启动在 `http://localhost:8000`。
