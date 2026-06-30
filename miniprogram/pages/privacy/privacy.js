Page({
  onLoad() {
    wx.setNavigationBarTitle({ title: '隐私说明' })
  },

  goHome() {
    wx.reLaunch({ url: '/pages/index/index' })
  }
})

