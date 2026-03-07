import React from 'react'
import UrgencyBadge from './UrgencyBadge'
import CategoryBadge from './CategoryBadge'

export default function ThreadCard({ thread, onClick, isSelected }) {
    const urgencyColors = {
        critical: 'bg-red-500',
        high: 'bg-orange-500',
        medium: 'bg-yellow-500',
        low: 'bg-green-500',
    }

    const typeColorMap = {
        tenant: 'bg-blue-100 text-blue-700',
        contractor: 'bg-purple-100 text-purple-700',
        prospect: 'bg-green-100 text-green-700',
        legal: 'bg-red-100 text-red-700',
        internal: 'bg-slate-100 text-slate-700',
    }

    return (
        <div
            onClick={onClick}
            className={`relative group cursor-pointer border rounded-xl overflow-hidden transition-all duration-200 hover:shadow-md ${isSelected
                    ? 'bg-blue-50 border-blue-200'
                    : 'bg-white border-slate-100 hover:bg-slate-50'
                }`}
        >
            {/* Left urgency bar */}
            <div className={`absolute left-0 top-0 bottom-0 w-1 ${urgencyColors[thread.urgency] || 'bg-slate-200'}`} />

            <div className="flex items-center p-4 gap-4">
                {/* Urgency dot */}
                <div className="shrink-0 flex items-center justify-center w-8">
                    <div className={`w-3 h-3 rounded-full ${urgencyColors[thread.urgency] || 'bg-slate-200'} ${thread.urgency === 'critical' ? 'animate-pulse' : ''}`} />
                </div>

                {/* Center content */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                        <h3 className={`text-sm truncate ${thread.is_unread ? 'font-bold text-slate-900' : 'font-semibold text-slate-700'}`}>
                            {thread.subject}
                        </h3>
                        {thread.is_unread && (
                            <div className="w-2 h-2 rounded-full bg-blue-500 shrink-0" title="Unread" />
                        )}
                        <CategoryBadge category={thread.category} />
                    </div>

                    <div className="text-sm text-slate-500 truncate mb-2">
                        {thread.is_analysed ? (
                            thread.ai_summary
                        ) : (
                            <span className="italic opacity-60">Awaiting analysis...</span>
                        )}
                    </div>

                    <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        <span className="text-slate-600">{thread.contact_name}</span>
                        <span className={`px-1.5 py-0.5 rounded ${typeColorMap[thread.contact_type] || 'bg-slate-100 text-slate-600'}`}>
                            {thread.contact_type}
                        </span>
                        <span className="opacity-30">•</span>
                        <span>{thread.property_name}</span>
                        <span className="opacity-30">•</span>
                        <span>{thread.message_count} messages</span>
                        <span className="opacity-30">•</span>
                        <span>{thread.last_message_at_relative || 'Recently'}</span>
                    </div>
                </div>

                {/* Right side badges */}
                <div className="shrink-0 flex flex-col items-end gap-2">
                    <UrgencyBadge level={thread.urgency} />
                    <div className="text-[10px] font-bold text-slate-400">
                        {thread.days_open} DAYS OPEN
                    </div>
                </div>
            </div>
        </div>
    )
}
