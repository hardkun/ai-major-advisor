// 本地 FastAPI 后端地址。
// 微信开发者工具本地演示时请勾选“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”。
const API_BASE = 'http://127.0.0.1:8000'

// 演示模式：用于作品集截图和本地演示。
// true 时 recommend 请求默认关闭 use_ai，避免 LLM 响应慢导致小程序超时。
// 如果后端请求失败，会展示本地 demo 推荐数据，并在页面标注“演示数据”。
const DEMO_MODE = true

const DEMO_RECOMMEND_RESULT = {
  log_id: null,
  report_id: null,
  is_demo_result: true,
  demo_message: '当前展示的是本地演示数据，用于作品集截图。请启动 FastAPI 后端后重试真实接口。',
  items: [
    {
      school_name: '成都信息工程大学',
      major_name: '人工智能',
      city: '成都',
      school_level: '普通本科',
      match_type: '稳',
      min_score: 589,
      min_rank: 35000,
      source_name: '成都信息工程大学本科招生官网',
      is_verified: true,
      reason: '你的位次与该专业往年最低录取位次较接近，可作为相对稳妥的参考选择。',
      ai_explanation: {
        recommend_reason: '该推荐基于已核验招生数据、分数/位次和目标方向生成。',
        study_focus: '该专业与 AI算法、大模型应用方向相关，适合关注算法、智能系统和 AI 应用开发的学生。',
        suitable_for: '适合数学基础较好、愿意持续学习编程和算法、对智能系统有兴趣的学生。',
        career_suggestions: '后续可关注算法工程、智能系统开发、AI 应用开发等方向。',
        risk_notice: '演示数据仅用于截图展示，不构成最终志愿填报建议。'
      }
    },
    {
      school_name: '天津工业大学',
      major_name: '计算机科学与技术',
      city: '天津',
      school_level: '双一流',
      match_type: '冲',
      min_score: 603,
      min_rank: 22000,
      source_name: '天津工业大学本科招生官网',
      is_verified: true,
      reason: '该专业往年最低位次相对更靠前，可作为冲刺参考选择。',
      ai_explanation: {
        recommend_reason: '该专业覆盖编程基础、数据结构、算法和软件工程能力，可作为进入 AI 应用开发方向的基础。',
        study_focus: '建议重点关注程序设计、数据结构、算法、数据库、操作系统和软件工程。',
        suitable_for: '适合逻辑能力较强、愿意长期写代码并持续提升工程能力的学生。',
        career_suggestions: '后续可关注后端开发、AI 应用开发、软件工程、数据平台等方向。',
        risk_notice: '演示数据仅用于截图展示，不构成最终志愿填报建议。'
      }
    }
  ],
  disclaimer: '演示数据仅用于作品集截图。本系统正式结果应以已核验公开数据和官方招生信息为准，不构成最终志愿填报建议。'
}

module.exports = {
  API_BASE,
  DEMO_MODE,
  DEMO_RECOMMEND_RESULT
}
