Page({
  onLoad() {
    wx.setNavigationBarTitle({ title: '产品说明' })
  },

  goHome() {
    wx.reLaunch({ url: '/pages/index/index' })
  }
})

