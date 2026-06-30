const { request } = require('../../utils/request')

Page({
  data: {
    form: {
      province: '四川',
      score: '',
      rank: '',
      subject_type: '物理类',
      target_direction: '机器人',
      use_ai: true
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
    targetDirectionIndex: 0,
    loading: false
  },

  onLoad() {
    wx.setNavigationBarTitle({ title: 'AI专业择校助手' })
  },

  onInput(event) {
    const field = event.currentTarget.dataset.field
    this.setData({
      [`form.${field}`]: event.detail.value
    })
  },

  onSubjectTypeChange(event) {
    const index = Number(event.detail.value)
    this.setData({
      subjectTypeIndex: index,
      'form.subject_type': this.data.subjectTypes[index]
    })
  },

  onTargetDirectionChange(event) {
    const index = Number(event.detail.value)
    this.setData({
      targetDirectionIndex: index,
      'form.target_direction': this.data.targetDirections[index]
    })
  },

  onUseAIChange(event) {
    this.setData({
      'form.use_ai': event.detail.value
    })
  },

  async submitRecommend() {
    if (this.data.loading) {
      return
    }

    const form = this.data.form
    if (form.score === '' || form.rank === '') {
      wx.showToast({
        title: '请填写分数和位次',
        icon: 'none'
      })
      return
    }

    const score = Number(form.score)
    const rank = Number(form.rank)
    if (!Number.isFinite(score) || score < 0 || !Number.isFinite(rank) || rank <= 0) {
      wx.showToast({
        title: '请输入有效的分数和位次',
        icon: 'none'
      })
      return
    }

    this.setData({ loading: true })
    wx.showLoading({ title: '正在生成推荐', mask: true })

    try {
      const result = await request({
        url: '/recommend',
        method: 'POST',
        data: {
          province: form.province.trim(),
          score,
          rank,
          subject_type: form.subject_type,
          target_direction: form.target_direction,
          use_ai: form.use_ai
        }
      })

      wx.setStorageSync('recommend_result', result)
      wx.navigateTo({ url: '/pages/result/result' })
    } catch (error) {
      wx.showToast({
        title: error.message || '生成推荐失败',
        icon: 'none',
        duration: 2500
      })
    } finally {
      wx.hideLoading()
      this.setData({ loading: false })
    }
  }
})
