# 部署指南与环境变量配置

本项目的前端部分可以轻松部署到 Vercel、Netlify 等现代云托管平台。为了确保应用在生产环境中正确连接到后端 API，并且不显示假数据（Mock 数据），请务必阅读以下配置指南。

## 1. 核心环境变量说明

| 变量名 | 作用 | 推荐值 (开发) | 推荐值 (生产) |
| --- | --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | 后端 API 的实际请求地址 | `http://localhost:8000/api` | 真实的公网网关 (如 `https://api.orca.yuki/api`) |
| `NEXT_PUBLIC_USE_MOCK_API` | 是否强制拦截请求并使用前端假数据 | `true` | `false` |

## 2. `.env.local` 文件的局限性

在开发期间，您的环境变量往往存放在根目录的 `.env.local` 文件中。
> [!WARNING]
> `.env.local` 已经被加入到 `.gitignore` 中，它**不会**被提交到 Git 仓库，也**不会**在云端部署时生效！

## 3. 完整部署顺序

为了保证应用稳定上线，推荐按照以下顺序进行：

1. **先部署后端**：将 FastAPI 后端部署到您的服务器或托管平台。
2. **拿到公网 API URL**：确保后端服务正常运行，并获得类似 `https://api.orca.yuki/api` 的公网地址。
3. **在 Vercel/Netlify 配 NEXT_PUBLIC_API_URL**：进入前端项目的 Settings > Environment Variables，将地址配入。
4. **配 NEXT_PUBLIC_USE_MOCK_API=false**：在同页面添加该变量，确保生产环境不使用假数据。
5. **Redeploy 前端**：保存环境变量后，重新触发一次部署 (Redeploy)。
6. **打开线上页面确认没有红色 warning**：访问您部署好的前端域名，确认页面顶部没有红色的 `Deployment Warning` 横幅。

## 4. 常见的线上错配问题拦截

如果您将前端部署到了公网（如 `https://orca-trading.vercel.app`），但忘记修改环境变量，此时 `API_BASE_URL` 会错误地回退至默认的 `http://localhost:8000/api`。

为了防止这种“上线了但依然在连开发者本地电脑”的致命错误，前端内置了**运行时主动拦截器**。如果它侦测到当前的访问域名不是 `localhost`，但您的 API 却仍然配置为 `localhost`，它将在页面最顶部弹出一个不可忽略的红色警告横幅，提醒您及时前往托管平台更新环境变量配置。

## 5. Pre-deploy Checklist

在您正式推送代码或触发生产环境的构建之前，请确保完成以下自检项：

- [ ] `NEXT_PUBLIC_API_URL` 已配置成真实的云端后端地址（非 localhost）。
- [ ] `NEXT_PUBLIC_USE_MOCK_API=false`（已关闭假数据模拟）。
- [ ] 本地运行 `npm run lint` 检查通过，无关键警告和错误。
- [ ] 本地运行 `npm run build` 构建通过。
- [ ] （可选）本地运行 `npm run start` 打开生产预览，确认页面左下角**没有** Dev 面板。
- [ ] （可选）如果通过局域网/远程域名访问，并且 API 仍指向 localhost，会看到页面顶部的红色 Deployment Warning。
