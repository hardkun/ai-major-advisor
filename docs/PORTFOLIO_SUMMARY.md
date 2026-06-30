# 作品集项目一页介绍

## 项目名称

AI专业择校助手｜AI相关专业推荐与招生数据采集系统

## 项目一句话

一个围绕公开招生数据采集、人工核验、推荐匹配和 AI 解释生成的 AI 相关专业择校参考系统。

## 技术栈

- 后端：Python、FastAPI、SQLite、Pydantic
- 数据采集：requests、BeautifulSoup、openpyxl、pdfplumber
- AI：OpenAI-compatible LLM API
- 前端：原生微信小程序
- 后台：admin 原生 HTML / CSS / JavaScript
- 工具：采集日志、覆盖率报告、缺口诊断、项目健康检查脚本

## 核心能力展示

- FastAPI RESTful API 设计
- SQLite 数据库建模
- raw/admissions 双层数据治理
- HTML / Excel / PDF 招生数据解析
- 人工核验流程
- 推荐接口与冲稳保规则
- LLM 推荐解释生成
- 微信小程序展示
- admin 管理后台
- 项目边界和合规风险说明

## 业务流程图文字版

```text
公开招生数据源
  ↓
数据源检测 / 采集预览
  ↓
HTML / Excel / PDF 解析
  ↓
raw_admission_records
  ↓
人工核验
  ↓
admissions 正式推荐库
  ↓
recommend 推荐接口
  ↓
AI 解释生成
  ↓
微信小程序 / 报告页展示
```

## 项目边界

当前数据为部分高校公开数据验证集。

项目用于求职作品集展示，不作为真实志愿填报依据。

项目不承诺覆盖所有高校，不承诺录取概率，不替代官方志愿填报系统。

## 适合岗位

- AI 应用开发工程师
- LLM 应用开发工程师
- Python 后端开发
- AI 后端开发
- 数据采集 / 数据处理方向
- 数据工程助理
- FDE / 行业解决方案预备方向

## 演示方式

1. 启动后端：

```bash
python -m uvicorn main:app --reload
```

2. 打开 Swagger：

```text
http://127.0.0.1:8000/docs
```

3. 打开 admin：

```text
http://127.0.0.1:8000/admin
```

4. 微信小程序：

使用微信开发者工具打开 `miniprogram` 目录。
