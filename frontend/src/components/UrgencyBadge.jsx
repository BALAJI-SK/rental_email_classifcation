import React from 'react'

export default function UrgencyBadge({ level }) {
    const styles = {
        critical: 'bg-red-100 text-red-700',
        high: 'bg-orange-100 text-orange-700',
        medium: 'bg-yellow-100 text-yellow-700',
        low: 'bg-green-100 text-green-700',
    }

    const labels = {
        critical: 'Critical',
        high: 'High',
        medium: 'Medium',
        low: 'Low',
    }

    const baseStyle = styles[level] || 'bg-slate-100 text-slate-700'
    const label = labels[level] || 'Unknown'

    return (
        <div className={`px-2 py-0.5 rounded-full text-xs font-medium flex items-center gap-1.5 ${baseStyle}`}>
            {level === 'critical' && (
                <span className="w-1.5 h-1.5 rounded-full bg-red-600 animate-pulse-slow" />
            )}
            {label}
        </div>
    )
}
