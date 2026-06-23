# Orca Trading Yuki - 全栈部署说明

本文档记录了本项目“线上已接真实后端 + Supabase”的完整生产环境部署架构及关键配置。

## 1. Vercel 部署信息

### 1.1 前端 (Frontend)
- **Vercel 项目名**: `orca-trading-yuki-frontend`
- **线上 URL**: `https://orca-trading-yuki-frontend.vercel.app`
- **关键环境变量**:
  - `NEXT_PUBLIC_API_URL`: 配置为真实的后端地址（例如 `https://orca-trading-yuki-backend.vercel.app/api`）
  - `NEXT_PUBLIC_USE_MOCK_API`: `false` （必须关闭 Mock，连接真实后端）

### 1.2 后端 (Backend)
- **Vercel 项目名**: `orca-trading-yuki-backend`
- **线上 URL**: `https://orca-trading-yuki-backend.vercel.app`
- **关键环境变量**:
  - `ORCA_LLM_PROVIDER`: 对应的大模型提供商 (如 `anthropic`, `gemini`)
  - `ORCA_LLM_API_KEY`: 对应提供商的 API Key
  - `ORCA_CORS_ORIGINS`: 允许跨域访问的前端地址 (如 `https://orca-trading-yuki-frontend.vercel.app`)
  - `ORCA_DATABASE_URL`: 生产环境的 Postgres 数据库连接串（**注意：切勿将真实的 URL 提交到代码库中**）

## 2. 数据库配置 (Supabase)

本项目支持本地 SQLite 与云端 Postgres (Supabase) 双重数据存储模式。

### 2.1 数据库架构
- **Supabase Project Ref**: `ljwehohlxforjwoiwckq`
- **当前包含的数据表**:
  1. `runs`: 存储主分析任务的记录（ID、Symbol、Trade Date、状态等）
  2. `run_details`: 存储具体任务的分析结果和详细内容（决策建议、上下文等）

### 2.2 本地 vs 云端切换
- **本地开发**: 默认无需任何配置，项目会自动在 `backend/` 目录下生成 `runs.db` 文件，使用 **SQLite** 存储数据，方便快速启动和开发。
- **云端部署**:
  只需在 Vercel（或其他生产环境）配置 `ORCA_DATABASE_URL` 环境变量即可。
  一旦系统检测到 `ORCA_DATABASE_URL` 的存在，将自动无缝切换到 **Postgres (Supabase)** 进行数据持久化。
  *(不需要修改任何业务代码，通过环境变量驱动。)*

> [!CAUTION]
> 为了安全起见，绝对**不要**将真实的 `ORCA_DATABASE_URL` 硬编码在代码中或提交到 `.env` / Git 仓库内，请始终在云平台的配置控制面板中填入该值。
