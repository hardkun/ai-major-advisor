Page({
  onLoad() {
    wx.setNavigationBarTitle({ title: '免责声明' })
  },

  goHome() {
    wx.reLaunch({ url: '/pages/index/index' })
  }
})

