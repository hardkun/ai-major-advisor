const { request } = require('../../utils/request')

Page({
  data: {
    reportId: null,
    loading: true,
    errorMessage: '',
    report: null,
    freeResult: null,
    paidUnlocked: false,
    paying: false
  },

  onLoad(options) {
    wx.setNavigationBarTitle({ title: '报告详情' })

    const reportId = Number(options.report_id)
    if (!reportId) {
      this.setData({
        loading: false,
        errorMessage: '报告 ID 无效'
      })
      return
    }

    this.setData({ reportId })
    this.loadReport(reportId)
  },

  async loadReport(reportId) {
    this.setData({
      loading: true,
      errorMessage: ''
    })
    wx.showLoading({ title: '正在加载报告', mask: true })

    try {
      const response = await request({
        url: `/reports/${reportId}`,
        method: 'GET'
      })

      const normalized = this.normalizeReport(response)

      this.setData({
        report: normalized.report,
        freeResult: normalized.freeResult,
        paidUnlocked: Boolean(response.is_paid)
      })
    } catch (error) {
      this.setData({
        errorMessage: error.message || '报告加载失败'
      })
      wx.showToast({
        title: error.message || '报告加载失败',
        icon: 'none',
        duration: 2500
      })
    } finally {
      wx.hideLoading()
      this.setData({ loading: false })
    }
  },

  normalizeReport(response) {
    const freeResult = response.free_result
      ? {
          ...response.free_result,
          items: this.decorateItems(response.free_result.items)
        }
      : null

    const paidResult = response.paid_result
      ? {
          ...response.paid_result,
          items: this.decorateItems(response.paid_result.items)
        }
      : null

    return {
      report: {
        ...response,
        paid_result: paidResult
      },
      freeResult
    }
  },

  decorateItems(items) {
    if (!Array.isArray(items)) {
      return []
    }

    return items.map((item) => ({
      ...item,
      matchClass: this.getMatchClass(item.match_type)
    }))
  },

  getMatchClass(matchType) {
    const classMap = {
      冲: 'match-rush',
      稳: 'match-steady',
      保: 'match-safe'
    }
    return classMap[matchType] || 'match-default'
  },

  unlockPaidReport() {
    wx.showModal({
      title: '演示版提示',
      content: '当前为作品集演示版本，暂未接入真实微信支付。点击确认后将调用模拟支付接口解锁完整报告。',
      confirmText: '确认解锁',
      cancelText: '暂不解锁',
      success: (result) => {
        if (result.confirm) {
          this.submitMockPay()
        }
      }
    })
  },

  async submitMockPay() {
    if (this.data.paying || !this.data.reportId) {
      return
    }

    this.setData({ paying: true })
    wx.showLoading({ title: '正在模拟解锁', mask: true })
    let unlockSucceeded = false

    try {
      const response = await request({
        url: `/reports/${this.data.reportId}/mock-pay`,
        method: 'POST'
      })
      const normalized = this.normalizeReport(response)

      this.setData({
        report: normalized.report,
        freeResult: normalized.freeResult,
        paidUnlocked: true
      })
      unlockSucceeded = true
    } catch (error) {
      // 保持锁定状态，并在 finally 中统一提示。
    } finally {
      wx.hideLoading()
      this.setData({ paying: false })
      wx.showToast({
        title: unlockSucceeded ? '解锁成功' : '解锁失败，请稍后重试',
        icon: unlockSucceeded ? 'success' : 'none',
        duration: unlockSucceeded ? 1500 : 2500
      })
    }
  },

  retry() {
    if (this.data.reportId) {
      this.loadReport(this.data.reportId)
    }
  },

  goHome() {
    wx.reLaunch({ url: '/pages/index/index' })
  }
})
