const { API_BASE } = require('./config')

function buildErrorMessage(statusCode, data) {
  if (statusCode === 500) {
    return '后端服务异常（500），请查看 FastAPI 控制台日志。'
  }
  if (statusCode === 422) {
    return '请求参数格式错误（422），请检查省份、分数、位次、科类和方向字段。'
  }
  if (statusCode === 404) {
    return '接口不存在（404），请检查请求地址是否为 /recommend。'
  }

  const detail = data && data.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    return `请求参数校验失败：${detail.map((item) => item.msg).join('；')}`
  }
  return `请求失败：HTTP ${statusCode}`
}

function buildFailMessage(error) {
  const errMsg = error && error.errMsg ? error.errMsg : ''
  if (errMsg.includes('timeout')) {
    return '后端响应超时，请确认 FastAPI 服务是否启动，或临时关闭 AI 解释。'
  }
  if (errMsg.includes('fail')) {
    return '网络请求失败，请检查 API_BASE 是否为 http://127.0.0.1:8000，并确认后端已启动。'
  }
  return errMsg || '网络请求失败，请检查后端服务和微信开发者工具网络设置。'
}

function request(options = {}) {
  const {
    url = '',
    method = 'GET',
    data = {},
    header = {},
    timeout = 60000
  } = options

  const fullUrl = `${API_BASE}${url}`
  console.log('请求地址：', fullUrl)
  console.log('请求参数：', data)

  return new Promise((resolve, reject) => {
    wx.request({
      url: fullUrl,
      method: method.toUpperCase(),
      data,
      timeout,
      header: {
        'content-type': 'application/json',
        ...header
      },
      success(res) {
        console.log('响应结果：', res)
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
          return
        }
        reject(new Error(buildErrorMessage(res.statusCode, res.data)))
      },
      fail(err) {
        console.error('请求失败：', err)
        reject(new Error(buildFailMessage(err)))
      },
      complete(res) {
        console.log('请求完成：', res)
      }
    })
  })
}

module.exports = {
  request
}
