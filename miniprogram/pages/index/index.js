const { request } = require('../../utils/request')
const { DEMO_MODE, DEMO_RECOMMEND_RESULT } = require('../../utils/config')

Page({
  data: {
    form: {
      province: '四川',
      score: '',
      rank: '',
      subject_type: '物理类',
      target_direction: 'AI算法',
      // 演示阶段默认关闭 AI，优先保证 recommend 快速返回。
      use_ai: false
    },
    subjectTypes: ['物理类', '历史类'],
    subjectTypeIndex: 0,
    targetDirections: [
      '机器人',
      'AI算法',
      '大模型应用',
      'Agent',
      '计算机视觉',
      '智能制造'
    ],
    targetDirectionIndex: 1,
    loading: false,
    message: '',
    demoMode: DEMO_MODE
  },

  onLoad() {
    wx.setNavigationBarTitle({ title: 'AI专业择校助手' })
  },

  onInput(event) {
    const field = event.currentTarget.dataset.field
    this.setData({
      [`form.${field}`]: event.detail.value,
      message: ''
    })
  },

  onSubjectTypeChange(event) {
    const index = Number(event.detail.value)
    this.setData({
      subjectTypeIndex: index,
      'form.subject_type': this.data.subjectTypes[index],
      message: ''
    })
  },

  onTargetDirectionChange(event) {
    const index = Number(event.detail.value)
    this.setData({
      targetDirectionIndex: index,
      'form.target_direction': this.data.targetDirections[index],
      message: ''
    })
  },

  onUseAIChange(event) {
    this.setData({
      'form.use_ai': event.detail.value,
      message: ''
    })
  },

  normalizeRecommendResult(result) {
    const fallbackText = '该推荐基于已核验招生数据、分数/位次和目标方向生成。AI解释当前为演示降级模式，正式部署时可接入 LLM 生成更完整说明。'
    const items = Array.isArray(result.items) ? result.items : []
    return {
      ...result,
      items: items.map((item) => {
        if (item.ai_explanation && typeof item.ai_explanation === 'object') {
          return item
        }
        return {
          ...item,
          ai_explanation: {
            recommend_reason: typeof item.ai_explanation === 'string' ? item.ai_explanation : fallbackText,
            study_focus: fallbackText,
            suitable_for: '建议结合个人数学基础、编程兴趣和工程实践意愿综合判断。',
            career_suggestions: item.career_paths || '可关注 AI 应用开发、软件开发、数据处理、智能系统等方向。',
            risk_notice: '本结果仅基于当前验证集和规则算法生成，不构成最终志愿填报建议。'
          }
        }
      })
    }
  },

  buildRequestData() {
    const form = this.data.form
    const score = Number(form.score)
    const rank = Number(form.rank)
    return {
      province: form.province.trim(),
      score,
      rank,
      subject_type: form.subject_type,
      target_direction: form.target_direction,
      // DEMO_MODE 下强制关闭 AI，避免截图演示时等待 LLM。
      use_ai: DEMO_MODE ? false : Boolean(form.use_ai)
    }
  },

  validateForm() {
    const form = this.data.form
    if (form.score === '' || form.rank === '') {
      return '请填写分数和位次'
    }
    const score = Number(form.score)
    const rank = Number(form.rank)
    if (!Number.isFinite(score) || score < 0 || !Number.isFinite(rank) || rank <= 0) {
      return '请输入有效的分数和位次'
    }
    if (!form.province || !form.province.trim()) {
      return '请填写省份'
    }
    return ''
  },

  useLocalDemoResult(reason) {
    const result = this.normalizeRecommendResult({
      ...DEMO_RECOMMEND_RESULT,
      demo_message: reason || DEMO_RECOMMEND_RESULT.demo_message
    })
    wx.setStorageSync('recommend_result', result)
    wx.navigateTo({ url: '/pages/result/result' })
  },

  async submitRecommend() {
    if (this.data.loading) return

    const validateMessage = this.validateForm()
    if (validateMessage) {
      this.setData({ message: validateMessage })
      wx.showToast({ title: validateMessage, icon: 'none' })
      return
    }

    const requestData = this.buildRequestData()
    this.setData({
      loading: true,
      message: DEMO_MODE
        ? '演示模式已开启：本次请求默认关闭 AI 解释，优先保证快速返回。'
        : ''
    })
    wx.showLoading({ title: '推荐生成中...', mask: true })

    try {
      const result = await request({
        url: '/recommend',
        method: 'POST',
        data: requestData,
        timeout: 60000
      })

      const normalized = this.normalizeRecommendResult(result)
      if (!normalized.items || normalized.items.length === 0) {
        this.setData({
          message: '当前验证集没有匹配结果，请尝试调整分数、位次或方向。'
        })
      }
      wx.setStorageSync('recommend_result', normalized)
      wx.navigateTo({ url: '/pages/result/result' })
    } catch (error) {
      const message = error.message || '生成推荐失败，请检查后端服务。'
      console.error('生成推荐失败：', error)
      this.setData({ message })
      wx.showToast({ title: message, icon: 'none', duration: 3500 })

      if (DEMO_MODE) {
        setTimeout(() => {
          this.useLocalDemoResult(`真实接口请求失败：${message} 当前已切换为本地演示数据。`)
        }, 500)
      }
    } finally {
      wx.hideLoading()
      this.setData({ loading: false })
    }
  }
})
