# 正式简历项目经历

## A. AI应用开发工程师版本

项目名称：AI专业择校助手｜AI相关专业推荐与招生数据采集系统

- 设计并实现基于 FastAPI、SQLite、微信小程序和 LLM API 的 AI 相关专业择校参考系统，围绕公开招生数据采集、人工核验、推荐匹配和 AI 解释生成形成业务闭环。
- 接入 OpenAI-compatible LLM API，为推荐结果生成推荐理由、学习重点、适合人群、就业方向和风险提示，支持结构化 JSON 输出和异常兜底。
- 构建推荐结果结构化 schema，返回学校、专业、冲稳保类型、最低分、最低位次、数据来源、核验状态和 AI 解释，便于小程序和报告页展示。
- 实现 Human-in-the-loop 数据核验流程，自动采集数据先进入 raw 表，人工核验后才进入正式 admissions 推荐库，降低脏数据和 AI 幻觉风险。
- 优化高责任场景下的 AI 应用边界：推荐排序由规则算法和已核验数据决定，LLM 只负责解释，不直接决定推荐学校或专业。

## B. Python后端开发版本

项目名称：AI专业择校助手｜AI相关专业推荐与招生数据采集系统

- 设计并实现 FastAPI RESTful 后端，按 routers / schemas / crud / services 分层组织代码，覆盖推荐、报告、采集、核验和后台管理等模块。
- 构建 SQLite 数据模型，包括 schools、majors、admissions、raw_admission_records、raw_data_sources、collector_runs、reports 等核心表。
- 实现 `POST /recommend` 推荐接口和 `GET /reports/{report_id}` 报告接口，支持推荐日志保存、免费/完整报告结构和 mock-pay 演示流程。
- 构建本地 admin 管理后台，支持数据源新增、检测、预览、采集运行、采集日志查看、raw 数据核验和覆盖率报告展示。
- 优化后端可靠性，补充错误处理、AI 调用失败兜底、数据库轻量迁移、项目健康检查脚本和演示数据准备脚本。

## C. 数据工程 / 数据采集方向版本

项目名称：AI专业择校助手｜AI相关专业推荐与招生数据采集系统

- 构建公开招生数据采集管线，支持数据源发现、可采性检测、HTML 表格解析、Excel 解析、PDF 解析和附件型数据源处理。
- 设计 raw/admissions 双层数据表，自动采集数据进入 raw_admission_records，人工核验后写入 admissions，保证推荐接口只使用已核验数据。
- 实现字段映射、表头自动识别、rowspan/colspan 解析、宽表转换和采集预览能力，提升不同高校网页结构的适配效率。
- 构建 collector_runs 采集日志、coverage_report 覆盖率报告和 gap diagnosis 缺口诊断，用于跟踪数据源状态和数据覆盖情况。
- 设计测试源/示例源标记与官方候选源过滤机制，避免 demo 数据和第三方噪声影响真实高校公开数据验证集。
