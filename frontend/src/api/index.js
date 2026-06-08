import axios from 'axios'
import i18n from '../i18n'
import { supabase } from '../utils/supabase'

// 创建axios实例
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001',
  timeout: 3600000, // 60分钟超时（本地大模型生成本体需要较长时间）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
service.interceptors.request.use(
  async config => {
    config.headers['Accept-Language'] = i18n.global.locale.value
    
    // Inject X-User-Id header if user is authenticated
    let userId = null
    if (supabase) {
      try {
        const { data } = await supabase.auth.getSession()
        if (data?.session?.user) {
          userId = data.session.user.id
        }
      } catch (err) {
        console.error('Error getting Supabase session in interceptor:', err)
      }
    }
    
    // Fallback to bypass session in localStorage
    if (!userId) {
      try {
        const storedBypass = localStorage.getItem('lexior_bypass_session')
        if (storedBypass) {
          const bypassSession = JSON.parse(storedBypass)
          if (bypassSession?.user?.id) {
            userId = bypassSession.user.id
          }
        }
      } catch (err) {
        // Ignore
      }
    }
    
    if (userId) {
      config.headers['X-User-Id'] = userId
    }
    
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器（容错重试机制）
service.interceptors.response.use(
  response => {
    const res = response.data
    
    // 如果返回的状态码不是success，则抛出错误
    if (!res.success && res.success !== undefined) {
      console.error('API Error:', res.error || res.message || 'Unknown error')
      return Promise.reject(new Error(res.error || res.message || 'Error'))
    }
    
    return res
  },
  error => {
    console.error('Response error:', error)
    
    // 处理超时
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      console.error('Request timeout')
    }
    
    // 处理网络错误
    if (error.message === 'Network Error') {
      console.error('Network error - please check your connection')
    }
    
    return Promise.reject(error)
  }
)

// 带重试的请求函数
export const requestWithRetry = async (requestFn, maxRetries = 3, delay = 1000) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await requestFn()
    } catch (error) {
      if (i === maxRetries - 1) throw error
      
      console.warn(`Request failed, retrying (${i + 1}/${maxRetries})...`)
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)))
    }
  }
}

export default service
