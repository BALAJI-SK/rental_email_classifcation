import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL = 'ws://localhost:8000/ws'

export default function useWebSocket({
  onAnalysisProgress,
  onAnalysisComplete,
  onEscalation,
  onPatternDetected,
  onMorningBriefReady,
  onNewEmail,
  onThreadUpdated,
  onAnalysisStarted,
} = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState(null)
  const wsRef = useRef(null)
  const retryDelay = useRef(1000)
  const reconnectTimer = useRef(null)
  const unmounted = useRef(false)

  const callbacks = useRef({
    onAnalysisProgress,
    onAnalysisComplete,
    onEscalation,
    onPatternDetected,
    onMorningBriefReady,
    onNewEmail,
    onThreadUpdated,
    onAnalysisStarted
  })


  useEffect(() => {
    callbacks.current = {
      onAnalysisProgress,
      onAnalysisComplete,
      onEscalation,
      onPatternDetected,
      onMorningBriefReady,
      onNewEmail,
      onThreadUpdated,
      onAnalysisStarted
    }
  }, [onAnalysisProgress, onAnalysisComplete, onEscalation, onPatternDetected, onMorningBriefReady, onNewEmail, onThreadUpdated, onAnalysisStarted])

  const connect = useCallback(() => {
    if (unmounted.current) return

    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('✅ WebSocket Connected')
        setIsConnected(true)
        retryDelay.current = 1000
        const ping = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping')
        }, 20000)
        ws._pingInterval = ping
      }

      ws.onmessage = (e) => {
        let msg
        try { msg = JSON.parse(e.data) } catch { return }
        if (msg.event === 'pong') return

        setLastEvent(msg)

        const cb = callbacks.current
        switch (msg.event) {
          case 'analysis_progress':
            cb.onAnalysisProgress?.(msg)
            break
          case 'analysis_started':
            cb.onAnalysisStarted?.(msg)
            break
          case 'analysis_complete':
            cb.onAnalysisComplete?.(msg)
            break
          case 'escalation':
            cb.onEscalation?.(msg)
            break
          case 'pattern_detected':
            cb.onPatternDetected?.(msg)
            break
          case 'morning_brief_ready':
            cb.onMorningBriefReady?.(msg)
            break
          case 'new_email':
            cb.onNewEmail?.(msg)
            break
          case 'thread_updated':
            cb.onThreadUpdated?.(msg)
            break
          default:
            break
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        clearInterval(ws._pingInterval)
        if (!unmounted.current) {
          const delay = Math.min(retryDelay.current, 30000)
          retryDelay.current = delay * 2
          reconnectTimer.current = setTimeout(connect, delay)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      if (!unmounted.current) {
        reconnectTimer.current = setTimeout(connect, retryDelay.current)
        retryDelay.current = Math.min(retryDelay.current * 2, 30000)
      }
    }
  }, [])


  useEffect(() => {
    unmounted.current = false
    connect()
    return () => {
      console.log('🔌 Unmounting WebSocket hook')
      unmounted.current = true
      clearTimeout(reconnectTimer.current)
      if (wsRef.current && wsRef.current.readyState < 2) {
        wsRef.current.close()
      }
    }
  }, [connect])

  return { isConnected, lastEvent }
}
