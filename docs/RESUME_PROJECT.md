# 简历项目描述

## 项目名称

AI专业择校助手｜AI相关专业推荐与招生数据采集系统

## 一句话项目描述

基于 FastAPI、SQLite、微信小程序和 LLM API 构建的 AI 相关专业择校参考系统，围绕公开招生数据采集、结构化处理、人工核验、推荐匹配和 AI 解释生成实现完整业务闭环。

## A. AI应用开发岗位版

- 基于 OpenAI-compatible LLM API 实现推荐结果 AI 解释服务，生成推荐理由、学习重点、适合人群、就业方向和风险提示。
- 将大模型能力约束在“解释层”，推荐排序仍由规则算法和已核验招生数据决定，降低高责任场景中的幻觉风险。
- 设计 `RecommendRequest / RecommendResponse / AIExplanation` 等结构化输出 schema，保证前端展示和报告生成稳定。
- 构建推荐日志、免费报告、完整报告和 mock-pay 解锁流程，形成从推荐到报告的完整产品链路。
- 引入 Human-in-the-loop 数据核验流程，确保 AI 解释基于已核验数据，而不是直接编造院校专业建议。

## B. Python后端岗位版

- 使用 FastAPI 构建 RESTful 后端，按 routers / schemas / crud / services 分层组织代码，支持推荐、报告、采集、核验和后台管理接口。
- 使用 SQLite 设计 schools、majors、admissions、raw_admission_records、raw_data_sources、collector_runs、reports 等核心表。
- 实现 `POST /recommend` 推荐接口，支持省份、分数、位次、科类、目标方向和 AI 解释开关。
- 构建 admin 本地管理后台，支持数据源管理、采集预览、采集运行、raw 数据核验、覆盖率报告和缺口诊断。
- 实现数据库初始化和轻量迁移逻辑，保证旧数据不丢失，新增字段可平滑升级。
- 编写项目健康检查和演示数据准备脚本，提升项目可运行性和交付完整度。

## C. 数据工程 / AI数据应用岗位版

- 设计 raw/admissions 双层数据模型，自动采集数据先进入 raw 表，人工核验后才写入正式 admissions 推荐库。
- 支持公开招生数据源发现、可采性检测、HTML 表格解析、Excel 解析、PDF 表格解析和附件型数据源处理。
- 支持字段映射、表头自动识别、rowspan / colspan 表格解析、宽表转换和采集预览，适配不同高校网页结构。
- 建立 collector_runs 采集日志、coverage_report 覆盖率报告和 gap diagnosis 缺口诊断，辅助判断数据工程进度。
- 对测试源、示例源和第三方候选源进行标记和过滤，避免影响真实数据验证集。
- 通过人工核验流程控制数据质量，使推荐接口只使用已核验的正式 admissions 数据。
