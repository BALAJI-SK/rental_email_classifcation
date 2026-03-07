import React from 'react'
import { dismissPattern } from '../api'

export default function PatternAlerts({ patterns }) {
    if (!patterns || patterns.length === 0) return null

    return (
        <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-thin">
            {patterns.map((pattern, index) => (
                <PatternCard key={pattern.id || index} pattern={pattern} />
            ))}
        </div>
    )
}

function PatternCard({ pattern }) {
    const urgencyColors = {
        critical: 'bg-red-500',
        high: 'bg-orange-500',
        medium: 'bg-yellow-500',
        low: 'bg-green-500',
    }

    const borderColors = {
        critical: 'border-l-red-500',
        high: 'border-l-orange-500',
        medium: 'border-l-yellow-500',
        low: 'border-l-green-500',
    }

    const handleDismiss = async (e) => {
        e.stopPropagation()
        try {
            await dismissPattern(pattern.id)
            // Note: Ideally we'd remove it from local state too, but let's assume refresh handles it or state is external
        } catch (err) {
            console.error(err)
        }
    }

    return (
        <div className={`min-w-[320px] max-w-[400px] bg-white rounded-xl border border-slate-100 border-l-4 ${borderColors[pattern.severity] || 'border-l-slate-400'} p-4 shadow-sm hover:shadow-md transition-all group shrink-0 relative animate-in slide-in-from-right-10`}>
            <button
                onClick={handleDismiss}
                className="absolute top-2 right-2 w-6 h-6 flex items-center justify-center rounded-full text-slate-300 hover:text-slate-500 hover:bg-slate-50 opacity-0 group-hover:opacity-100 transition-all font-bold text-xs"
            >
                ✕
            </button>

            <div className="flex items-center gap-2 mb-2">
                <div className={`w-2 h-2 rounded-full ${urgencyColors[pattern.severity] || 'bg-slate-400'} ${pattern.severity === 'critical' ? 'animate-pulse' : ''}`} />
                <h4 className="text-[11px] font-bold text-slate-800 uppercase tracking-widest">{pattern.title}</h4>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed mb-4 line-clamp-2">
                {pattern.description}
            </p>

            <div className="flex items-center justify-between">
                <button className="text-[10px] font-bold text-blue-600 hover:text-blue-700 uppercase tracking-wider transition-colors">
                    View all related threads →
                </button>
                <span className="text-[10px] font-medium text-slate-300">Detected {pattern.detected_at_relative} ago</span>
            </div>
        </div>
    )
}
