import React, { useState } from 'react'
import useVoice from '../hooks/useVoice'
import { generateMorningBrief } from '../api'

export default function MorningBrief({ brief: initialBrief }) {
    const [brief, setBrief] = useState(initialBrief)
    const [isCollapsed, setIsCollapsed] = useState(false)
    const [isGenerating, setIsGenerating] = useState(false)
    const { speak, isSpeaking, stop } = useVoice()

    const handleGenerate = async () => {
        setIsGenerating(true)
        try {
            const newBrief = await generateMorningBrief()
            setBrief(newBrief)
        } catch (err) {
            console.error(err)
        } finally {
            setIsGenerating(false)
        }
    }

    const handleVoice = () => {
        if (isSpeaking) {
            stop()
        } else if (brief?.content) {
            speak(brief.content)
        }
    }

    if (!brief && !isGenerating) {
        return (
            <div className="bg-white border border-slate-100 rounded-2xl p-6 flex flex-col items-center gap-4 text-center">
                <h3 className="text-sm font-bold text-slate-900">☀️ Morning Brief</h3>
                <p className="text-xs text-slate-500 max-w-sm">No brief generated yet for today. Let AI summarize the overnight activity for you.</p>
                <button
                    onClick={handleGenerate}
                    className="h-10 px-6 bg-blue-600 text-white rounded-lg font-bold text-xs uppercase tracking-widest hover:bg-blue-700 transition-all"
                >
                    Generate Morning Brief
                </button>
            </div>
        )
    }

    return (
        <div className="bg-white border border-slate-100 rounded-2xl shadow-sm overflow-hidden transition-all duration-300">
            <div
                className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-slate-50 transition-colors"
                onClick={() => setIsCollapsed(!isCollapsed)}
            >
                <div className="flex items-center gap-3">
                    <span className="text-xl">☀️</span>
                    <h3 className="text-sm font-bold text-slate-900">Morning Brief</h3>
                    {isGenerating && (
                        <div className="flex gap-1 ml-2">
                            <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce" />
                            <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce delay-75" />
                            <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce delay-150" />
                        </div>
                    )}
                </div>
                <span className={`text-slate-400 transform transition-transform ${isCollapsed ? '' : 'rotate-180'}`}>▾</span>
            </div>

            {!isCollapsed && (
                <div className="px-6 pb-6 animate-in fade-in slide-in-from-top-2">
                    <div className="p-5 bg-orange-50/50 rounded-xl border border-orange-100/50">
                        {isGenerating ? (
                            <div className="space-y-4">
                                <div className="h-4 bg-orange-100 rounded w-3/4 animate-pulse" />
                                <div className="h-4 bg-orange-100 rounded w-5/6 animate-pulse" />
                                <div className="h-4 bg-orange-100 rounded w-2/3 animate-pulse" />
                            </div>
                        ) : (
                            <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                                {brief.content}
                            </div>
                        )}
                    </div>

                    <div className="mt-6 flex items-center gap-3">
                        <button
                            onClick={handleVoice}
                            disabled={isGenerating}
                            className={`h-9 px-4 rounded-lg flex items-center gap-2 font-bold text-[11px] uppercase tracking-widest transition-all ${isSpeaking
                                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-200'
                                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                                }`}
                        >
                            <span>{isSpeaking ? '⏹' : '🔊'}</span>
                            {isSpeaking ? 'Stop Listening' : 'Listen to Brief'}
                        </button>
                        <button
                            onClick={handleGenerate}
                            disabled={isGenerating}
                            className="h-9 px-4 bg-white border border-slate-200 text-slate-600 rounded-lg font-bold text-[11px] uppercase tracking-widest hover:border-slate-300 transition-all"
                        >
                            ↻ Regenerate
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
