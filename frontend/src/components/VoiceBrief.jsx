import React, { useState } from 'react'
import useVoice from '../hooks/useVoice'
import { fetchVoiceScript } from '../api'

export default function VoiceBrief({ inline = false }) {
    const { speak, stop, isSpeaking } = useVoice()
    const [loading, setLoading] = useState(false)

    const handleToggle = async () => {
        if (isSpeaking) {
            stop()
            return
        }

        setLoading(true)
        try {
            const { script } = await fetchVoiceScript()
            speak(script)
        } catch (err) {
            console.error('Failed to get voice script', err)
        } finally {
            setLoading(false)
        }
    }

    if (inline) {
        return (
            <button
                onClick={handleToggle}
                disabled={loading}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${isSpeaking
                        ? 'bg-blue-600 text-white shadow-lg'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
            >
                {loading ? (
                    <div className="w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                ) : isSpeaking ? (
                    <>
                        <div className="flex gap-0.5 items-end h-3">
                            <div className="w-0.5 bg-white animate-pulse" style={{ height: '60%' }} />
                            <div className="w-0.5 bg-white animate-pulse" style={{ height: '100%', animationDelay: '0.2s' }} />
                            <div className="w-0.5 bg-white animate-pulse" style={{ height: '40%', animationDelay: '0.4s' }} />
                        </div>
                        Playing
                    </>
                ) : (
                    <>
                        <span>🔊</span>
                        Listen
                    </>
                )}
            </button>
        )
    }

    return (
        <button
            onClick={handleToggle}
            disabled={loading}
            className={`fixed bottom-8 right-8 w-14 h-14 rounded-full shadow-2xl flex items-center justify-center transition-all transform hover:scale-110 active:scale-95 z-50 ${isSpeaking ? 'bg-blue-600' : 'bg-slate-900'
                }`}
        >
            {loading ? (
                <div className="w-6 h-6 border-3 border-slate-400 border-t-transparent rounded-full animate-spin" />
            ) : isSpeaking ? (
                <div className="flex gap-1 items-end h-6">
                    <div className="w-1.5 bg-white animate-pulse" style={{ height: '60%' }} />
                    <div className="w-1.5 bg-white animate-pulse" style={{ height: '100%', animationDelay: '0.2s' }} />
                    <div className="w-1.5 bg-white animate-pulse" style={{ height: '45%', animationDelay: '0.4s' }} />
                    <div className="w-1.5 bg-white animate-pulse" style={{ height: '80%', animationDelay: '0.1s' }} />
                </div>
            ) : (
                <span className="text-2xl">🔊</span>
            )}
        </button>
    )
}
