const FALLBACK_AI_EXPLANATION = {
  recommend_reason: '该推荐基于已核验招生数据、分数/位次和目标方向生成。AI解释当前为演示降级模式，正式部署时可接入 LLM 生成更完整说明。',
  study_focus: '建议重点关注数学基础、编程能力、数据结构、算法和工程实践。',
  suitable_for: '适合对计算机、人工智能和工程应用有兴趣，愿意持续学习编程的学生。',
  career_suggestions: '后续可关注 AI 应用开发、软件开发、数据处理、智能系统等方向。',
  risk_notice: '本结果仅基于当前验证集和规则算法生成，不构成最终志愿填报建议。'
}

Page({
  data: {
    hasResult: false,
    result: null,
    items: [],
    isDemoResult: false,
    demoMessage: ''
  },

  onLoad() {
    wx.setNavigationBarTitle({ title: 'AI专业推荐结果' })
  },

  onShow() {
    const result = wx.getStorageSync('recommend_result')
    if (!result || !Array.isArray(result.items)) {
      this.setData({
        hasResult: false,
        result: null,
        items: [],
        isDemoResult: false,
        demoMessage: ''
      })
      return
    }

    const items = result.items.map((item) => ({
      ...item,
      matchClass: this.getMatchClass(item.match_type),
      aiExpanded: false,
      ai_explanation: this.normalizeAIExplanation(item.ai_explanation, item),
      verifiedText: item.is_verified ? '已核验' : '待核验/未标注'
    }))

    this.setData({
      hasResult: true,
      result,
      items,
      isDemoResult: Boolean(result.is_demo_result),
      demoMessage: result.demo_message || ''
    })
  },

  normalizeAIExplanation(aiExplanation, item) {
    if (aiExplanation && typeof aiExplanation === 'object') {
      return {
        recommend_reason: aiExplanation.recommend_reason || FALLBACK_AI_EXPLANATION.recommend_reason,
        study_focus: aiExplanation.study_focus || FALLBACK_AI_EXPLANATION.study_focus,
        suitable_for: aiExplanation.suitable_for || FALLBACK_AI_EXPLANATION.suitable_for,
        career_suggestions: aiExplanation.career_suggestions || item.career_paths || FALLBACK_AI_EXPLANATION.career_suggestions,
        risk_notice: aiExplanation.risk_notice || FALLBACK_AI_EXPLANATION.risk_notice
      }
    }

    if (typeof aiExplanation === 'string' && aiExplanation) {
      return {
        ...FALLBACK_AI_EXPLANATION,
        recommend_reason: aiExplanation
      }
    }

    return FALLBACK_AI_EXPLANATION
  },

  getMatchClass(matchType) {
    const classMap = {
      冲: 'match-rush',
      稳: 'match-steady',
      保: 'match-safe'
    }
    return classMap[matchType] || 'match-default'
  },

  toggleAIExplanation(event) {
    const index = Number(event.currentTarget.dataset.index)
    const item = this.data.items[index]
    if (!item || !item.ai_explanation) return

    this.setData({
      [`items[${index}].aiExpanded`]: !item.aiExpanded
    })
  },

  viewReport() {
    const reportId = this.data.result && this.data.result.report_id
    if (!reportId) {
      wx.showToast({
        title: this.data.isDemoResult ? '演示数据暂无报告' : '暂无可查看的报告',
        icon: 'none'
      })
      return
    }

    wx.navigateTo({
      url: `/pages/report/report?report_id=${reportId}`
    })
  },

  goHome() {
    wx.reLaunch({ url: '/pages/index/index' })
  }
})
