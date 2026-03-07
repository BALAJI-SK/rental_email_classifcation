import React, { useEffect } from 'react'

export default function NotificationToast({ id, title, body, type, onClose, onClick }) {
    useEffect(() => {
        if (type !== 'critical') {
            const timer = setTimeout(onClose, 8000)
            return () => clearTimeout(timer)
        }
    }, [type, onClose])

    const typeStyles = {
        critical: 'border-l-red-500 bg-red-50',
        warning: 'border-l-orange-500 bg-orange-50',
        success: 'border-l-green-500 bg-green-50',
        info: 'border-l-blue-500 bg-blue-50',
    }

    const dotStyles = {
        critical: 'bg-red-500',
        warning: 'bg-orange-500',
        success: 'bg-green-500',
        info: 'bg-blue-500',
    }

    return (
        <div
            className={`w-80 pointer-events-auto cursor-pointer shadow-lg border-l-4 rounded-r-lg p-4 transition-all duration-300 transform translate-x-0 animate-in slide-in-from-right ${typeStyles[type] || typeStyles.info}`}
            onClick={onClick}
        >
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${dotStyles[type]} ${type === 'critical' ? 'animate-pulse' : ''}`} />
                    <h4 className="font-semibold text-sm text-slate-900">{title}</h4>
                </div>
                <button
                    onClick={(e) => { e.stopPropagation(); onClose(); }}
                    className="text-slate-400 hover:text-slate-600 outline-none"
                >
                    ✕
                </button>
            </div>
            <p className="mt-1 text-sm text-slate-600 line-clamp-2">{body}</p>
        </div>
    )
}
