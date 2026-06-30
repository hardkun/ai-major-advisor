const { API_BASE } = require('./config')

function request(options = {}) {
  const {
    url = '',
    method = 'GET',
    data = {},
    header = {}
  } = options

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE}${url}`,
      method: method.toUpperCase(),
      data,
      header: {
        'content-type': 'application/json',
        ...header
      },
      success(response) {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data)
          return
        }

        const detail = response.data && response.data.detail
        const message = typeof detail === 'string'
          ? detail
          : `请求失败（${response.statusCode}）`
        reject(new Error(message))
      },
      fail(error) {
        reject(new Error(error.errMsg || '网络请求失败，请检查后端服务'))
      }
    })
  })
}

module.exports = {
  request
}

