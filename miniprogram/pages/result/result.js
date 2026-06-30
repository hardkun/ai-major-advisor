Page({
  data: {
    hasResult: false,
    result: null,
    items: []
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
        items: []
      })
      return
    }

    const items = result.items.map((item) => ({
      ...item,
      matchClass: this.getMatchClass(item.match_type),
      aiExpanded: false
    }))

    this.setData({
      hasResult: true,
      result,
      items
    })
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
    if (!item || !item.ai_explanation) {
      return
    }

    this.setData({
      [`items[${index}].aiExpanded`]: !item.aiExpanded
    })
  },

  viewReport() {
    const reportId = this.data.result && this.data.result.report_id
    if (!reportId) {
      wx.showToast({
        title: '暂无可查看的报告',
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

