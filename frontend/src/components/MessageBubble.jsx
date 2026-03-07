import React, { useState } from 'react'

export default function MessageBubble({ message }) {
    const [expanded, setExpanded] = useState(false)
    const isInternal = message.sender_type === 'pm' || message.sender_type === 'system'

    const typeColorMap = {
        tenant: 'bg-blue-100 text-blue-700',
        contractor: 'bg-purple-100 text-purple-700',
        prospect: 'bg-green-100 text-green-700',
        legal: 'bg-red-100 text-red-700',
        pm: 'bg-slate-800 text-white',
        system: 'bg-slate-200 text-slate-700',
    }

    const lines = message.body.split('\n')
    const shouldTruncate = lines.length > 3 && !expanded

    return (
        <div className={`flex flex-col ${isInternal ? 'items-end' : 'items-start'} mb-6`}>
            <div className={`flex items-center gap-2 mb-1 text-[10px] font-bold uppercase tracking-widest ${isInternal ? 'flex-row-reverse' : ''}`}>
                <span className="text-slate-900">{message.sender_name}</span>
                <span className={`px-1 rounded-[2px] ${typeColorMap[message.sender_type] || 'bg-slate-100 text-slate-600'}`}>
                    {message.sender_type}
                </span>
                <span className="text-slate-400 font-medium lowercase italic">{message.timestamp_relative} ago</span>
                <span title="via Email">✉️</span>
            </div>

            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm transition-all ${isInternal
                    ? 'bg-blue-600 text-white rounded-tr-none'
                    : 'bg-slate-100 text-slate-800 rounded-tl-none'
                }`}>
                <div className={`whitespace-pre-wrap break-words leading-relaxed ${shouldTruncate ? 'max-h-24 overflow-hidden' : ''}`}>
                    {message.body}
                </div>

                {lines.length > 3 && (
                    <button
                        onClick={() => setExpanded(!expanded)}
                        className={`mt-2 text-[10px] font-bold uppercase tracking-wider ${isInternal ? 'text-blue-200 hover:text-white' : 'text-blue-600 hover:text-blue-700'}`}
                    >
                        {expanded ? 'Show less' : 'Show more'}
                    </button>
                )}

                {message.attachments && message.attachments.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2 pt-4 border-t border-white/20 select-none">
                        {message.attachments.map((file, i) => (
                            <div key={i} className={`flex items-center gap-2 px-2 py-1 rounded text-[10px] font-medium border ${isInternal ? 'bg-white/10 border-white/20' : 'bg-white border-slate-200'}`}>
                                <span>📎</span>
                                <span className="truncate max-w-[120px]">{file.name}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
