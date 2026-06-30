# 部署说明

## 本地运行

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

如果系统没有全局 python，也可以使用已有 `.venv`：

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

## 环境变量

项目使用 `.env` 读取配置。常用字段：

```env
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=

SEARCH_PROVIDER=bocha
SEARCH_API_KEY=
SEARCH_API_URL=https://api.bochaai.com/v1/web-search
SEARCH_RESULT_LIMIT=10
SEARCH_DEBUG=false
```

说明：

- `LLM_API_KEY`：AI 解释服务使用的大模型 API Key。
- `LLM_BASE_URL`：OpenAI-compatible API 地址。
- `LLM_MODEL`：模型名称。
- `SEARCH_PROVIDER`：搜索 Provider，当前支持 bocha / serper / generic。
- `SEARCH_API_KEY`：搜索 API Key。
- `SEARCH_API_URL`：搜索 API 地址。

## 数据库

默认使用 SQLite。

数据库文件：

```text
data/advisor.db
```

首次运行后端时，`db.py` 会自动初始化所需数据表，并执行轻量字段迁移。

## 管理后台

后端启动后访问：

```text
http://127.0.0.1:8000/admin
```

当前 admin 是本地演示版，没有登录权限控制。正式上线前必须增加管理员认证、操作审计和权限隔离。

## 微信小程序配置

小程序 API 地址在：

```text
miniprogram/utils/config.js
```

本地开发时：

```js
const API_BASE = "http://127.0.0.1:8000";
```

部署到云服务器后，需要改为后端公网 HTTPS 地址，并在微信公众平台配置合法域名。

## 部署建议

后端可以部署到：

- 云服务器
- Render
- Railway
- Fly.io
- 其他支持 Python/FastAPI 的平台

上线前建议补充：

- 管理后台登录和权限控制
- 正式隐私政策
- 数据来源授权与合规审查
- HTTPS
- 定期备份 SQLite 或迁移到 PostgreSQL
- 真实支付回调替换 mock-pay
