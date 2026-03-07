import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const fetchDashboard = () =>
  api.get('/dashboard').then(r => r.data)

export const fetchThreads = (filters = {}) =>
  api.get('/threads', { params: { per_page: 200, ...filters } }).then(r => r.data.threads || [])

export const fetchThread = (id) =>
  api.get(`/threads/${id}`).then(r => r.data)

export const updateThread = (id, data) =>
  api.patch(`/threads/${id}`, data).then(r => r.data)

export const triggerAnalysis = (id) =>
  api.post(`/threads/${id}/analyse`).then(r => r.data)

export const triggerAnalyseAll = () =>
  api.post('/analyse/all').then(r => r.data)

export const fetchMorningBrief = () =>
  api.get('/dashboard/morning-brief').then(r => r.data)

export const generateMorningBrief = () =>
  api.post('/dashboard/morning-brief').then(r => r.data)

export const fetchProperties = () =>
  api.get('/properties').then(r => r.data)

export const fetchContacts = () =>
  api.get('/contacts').then(r => r.data)

export const fetchPatterns = () =>
  api.get('/dashboard/patterns').then(r => r.data.alerts || [])

export const dismissPattern = (id) =>
  api.post(`/dashboard/patterns/${id}/dismiss`).then(r => r.data)

export const simulateEmail = (scenario) =>
  api.post('/demo/simulate-email', { scenario }).then(r => r.data)

export const fetchVoiceScript = () =>
  api.get('/notifications/voice-script').then(r => r.data)

export const exportExcel = (type, filters = {}) =>
  api.get(`/exports/${type}`, {
    params: filters,
    responseType: 'blob',
  }).then(r => {
    const url = window.URL.createObjectURL(r.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `lette-${type}-${Date.now()}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
  })

export const sendChat = (query) =>
  api.post('/chat', { query }).then(r => r.data.response || r.data)


export default api
