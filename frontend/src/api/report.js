import service, { requestWithRetry } from './index'

/**
 * 开始报告生成
 * @param {Object} data - { simulation_id, force_regenerate? }
 */
export const generateReport = (data) => {
  return requestWithRetry(() => service.post('/api/report/generate', data), 3, 1000)
}

/**
 * 获取报告生成状态
 * @param {string} reportId
 */
export const getReportStatus = (reportId) => {
  return service.get(`/api/report/generate/status`, { params: { report_id: reportId } })
}

/**
 * 获取 Agent 日志（增量）
 * @param {string} reportId
 * @param {number} fromLine - 从第几行开始获取
 */
export const getAgentLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/agent-log`, { params: { from_line: fromLine } })
}

/**
 * 获取控制台日志（增量）
 * @param {string} reportId
 * @param {number} fromLine - 从第几行开始获取
 */
export const getConsoleLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/console-log`, { params: { from_line: fromLine } })
}

/**
 * 获取报告详情
 * @param {string} reportId
 */
export const getReport = (reportId) => {
  return service.get(`/api/report/${reportId}`)
}

/**
 * 与 Report Agent 对话
 * @param {Object} data - { simulation_id, message, chat_history? }
 */
export const chatWithReport = (data) => {
  return requestWithRetry(() => service.post('/api/report/chat', data), 3, 1000)
}

/**
 * 与虚拟对手谈判
 * @param {Object} data - { simulation_id, message, chat_history? }
 */
export const negotiateWithOpponent = (data) => {
  return requestWithRetry(() => service.post('/api/report/negotiate', data), 3, 1000)
}

/**
 * Get podcast generation status
 * @param {string} reportId
 */
export const getPodcastStatus = (reportId) => {
  return service.get(`/api/report/${reportId}/podcast/status`)
}

/**
 * Generate a podcast (type: 'discussions' or 'overview')
 * @param {string} reportId
 * @param {Object} data - { type: 'discussions' | 'overview' }
 */
export const generatePodcast = (reportId, data) => {
  return service.post(`/api/report/${reportId}/podcast/generate`, data)
}

export const getActiveUserIdSync = () => {
  try {
    const storedBypass = localStorage.getItem('lexior_bypass_session')
    if (storedBypass) {
      const bypassSession = JSON.parse(storedBypass)
      if (bypassSession?.user?.id) {
        return bypassSession.user.id
      }
    }
  } catch (err) {}

  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith('sb-') && key.endsWith('-auth-token')) {
        const value = localStorage.getItem(key)
        if (value) {
          const parsed = JSON.parse(value)
          if (parsed?.user?.id) {
            return parsed.user.id
          }
        }
      }
    }
  } catch (err) {}

  return null
}

/**
 * Get podcast play URL
 * @param {string} reportId
 * @param {string} type - 'discussions' | 'overview'
 */
export const getPodcastAudioUrl = (reportId, type) => {
  const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001'
  const userId = getActiveUserIdSync()
  const userParam = userId ? `&userId=${userId}` : ''
  return `${baseURL}/api/report/${reportId}/podcast/download?type=${type}${userParam}`
}

/**
 * Exporte le rapport en PDF
 * @param {string} reportId
 */
export const exportReportPDF = (reportId) => {
  return service.get(`/api/report/${reportId}/export-pdf`, { responseType: 'blob' })
}
