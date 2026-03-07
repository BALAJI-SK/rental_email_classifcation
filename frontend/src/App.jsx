import React, { useState, useEffect, useCallback } from 'react'
import * as api from './api'
import useWebSocket from './hooks/useWebSocket'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import ThreadDetail from './components/ThreadDetail'
import SearchBar from './components/SearchBar'
import AnalyseButton from './components/AnalyseButton'
import SimulateButton from './components/SimulateButton'
import NotificationToast from './components/NotificationToast'

export default function App() {
  const [threads, setThreads] = useState([])
  const [selectedThreadId, setSelectedThreadId] = useState(null)
  const [dashboardStats, setDashboardStats] = useState(null)
  const [morningBrief, setMorningBrief] = useState(null)
  const [patterns, setPatterns] = useState([])
  const [analysisProgress, setAnalysisProgress] = useState(null)
  const [filters, setFilters] = useState({
    properties: [],
    urgencies: ['critical', 'high', 'medium', 'low'],
    categories: [],
    status: 'open'
  })
  const [toasts, setToasts] = useState([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { ...toast, id }])
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const refreshData = useCallback(async () => {
    try {
      const [dashboardData, threadData, patternData, briefData] = await Promise.all([
        api.fetchDashboard(),
        api.fetchThreads(),
        api.fetchPatterns(),
        api.fetchMorningBrief()
      ])
      setDashboardStats(dashboardData.stats || dashboardData)
      setThreads(Array.isArray(threadData) ? threadData : [])
      setPatterns(Array.isArray(patternData) ? patternData : [])
      setMorningBrief(briefData.morning_brief || briefData)
    } catch (err) {
      console.error('Failed to refresh data', err)
    }
  }, [])

  const { isConnected: wsConnected } = useWebSocket({
    onAnalysisProgress: (msg) => setAnalysisProgress(msg.data),
    onAnalysisComplete: (msg) => {
      setAnalysisProgress(null)
      refreshData()
      addToast({ title: 'Analysis Complete', body: 'All threads have been analysed.', type: 'success' })
    },
    onEscalation: (msg) => {
      refreshData()
      addToast({ title: 'Urgent Escalation', body: msg.data.summary, type: 'critical', threadId: msg.data.thread_id })
    },
    onPatternDetected: (msg) => {
      setPatterns(prev => [msg.data, ...prev])
      addToast({ title: 'New Pattern Detected', body: msg.data.title, type: 'warning' })
    },
    onMorningBriefReady: (msg) => {
      setMorningBrief(msg.data)
      addToast({ title: 'Morning Brief Ready', body: 'Your AI summary is updated.', type: 'info' })
    },
    onNewEmail: (msg) => {
      if (!msg.data) return
      setThreads(prev => [msg.data, ...prev])
      const sender = msg.data.sender_name || msg.data.participant_names || 'Someone'
      addToast({
        title: 'New Message',
        body: `From ${sender}`,
        type: 'info',
        threadId: msg.data.id
      })
    },
    onThreadUpdated: (msg) => {
      if (!msg?.data?.id) return
      setThreads(prev => prev.map(t => t?.id === msg.data.id ? msg.data : t))
    }
  })

  useEffect(() => {
    refreshData()
  }, [refreshData])

  const selectedThread = Array.isArray(threads)
    ? threads.find(t => t && t.id === selectedThreadId)
    : null

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      <Sidebar
        threads={threads}
        filters={filters}
        setFilters={setFilters}
        dashboardStats={dashboardStats}
        analysisProgress={analysisProgress}
        onMorningBriefReady={() => { }} // Handle voice here or in hook
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <header className="h-16 border-b bg-white flex items-center gap-4 px-4 lg:px-6 shrink-0 z-10">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden w-10 h-10 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-500"
          >
            ☰
          </button>

          <SearchBar onSearch={setSearchQuery} />

          <div className="flex items-center gap-4">
            <SimulateButton onSimulate={api.simulateEmail} />
            <AnalyseButton
              progress={analysisProgress}
              onAnalyse={api.triggerAnalyseAll}
            />
          </div>
        </header>

        <div className="flex-1 overflow-y-auto scrollbar-thin">
          <Dashboard
            stats={dashboardStats}
            threads={threads.filter(t =>
              searchQuery === '' ||
              t.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
              t.ai_summary?.toLowerCase().includes(searchQuery.toLowerCase()) ||
              t.property_name?.toLowerCase().includes(searchQuery.toLowerCase())
            )}
            filters={filters}
            patterns={patterns}
            morningBrief={morningBrief}
            onSelectThread={setSelectedThreadId}
            selectedThreadId={selectedThreadId}
          />
        </div>

        {/* Notifications */}
        <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
          {toasts.map(toast => (
            <NotificationToast
              key={toast.id}
              {...toast}
              onClose={() => removeToast(toast.id)}
              onClick={() => {
                if (toast.threadId) setSelectedThreadId(toast.threadId)
                removeToast(toast.id)
              }}
            />
          ))}
        </div>
      </main>

      {/* Right Drawer */}
      {selectedThread && (
        <ThreadDetail
          thread={selectedThread}
          onClose={() => setSelectedThreadId(null)}
          onUpdate={(updated) => setThreads(prev => prev.map(t => t.id === updated.id ? updated : t))}
        />
      )}
    </div>
  )
}
