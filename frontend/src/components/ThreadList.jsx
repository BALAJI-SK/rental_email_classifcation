import React, { useState, useMemo } from 'react'
import ThreadCard from './ThreadCard'

export default function ThreadList({ threads, onSelectThread, selectedThreadId, loading }) {
    const [sortBy, setSortBy] = useState('urgency')

    const sortedThreads = useMemo(() => {
        const list = [...threads]
        const urgencyMap = { critical: 0, high: 1, medium: 2, low: 3 }

        switch (sortBy) {
            case 'urgency':
                return list.sort((a, b) => urgencyMap[a.urgency] - urgencyMap[b.urgency])
            case 'newest':
                return list.sort((a, b) => new Date(b.last_message_at) - new Date(a.last_message_at))
            case 'oldest':
                return list.sort((a, b) => new Date(a.last_message_at) - new Date(b.last_message_at))
            case 'days_open':
                return list.sort((a, b) => b.days_open - a.days_open)
            default:
                return list
        }
    }, [threads, sortBy])

    if (loading) {
        return (
            <div className="space-y-4">
                {[...Array(6)].map((_, i) => (
                    <div key={i} className="h-24 bg-white rounded-xl border border-slate-100 animate-pulse" />
                ))}
            </div>
        )
    }

    if (threads.length === 0) {
        return (
            <div className="py-20 flex flex-col items-center justify-center text-center">
                <div className="text-6xl mb-4">🏖️</div>
                <h3 className="text-lg font-bold text-slate-800">All caught up!</h3>
                <p className="text-sm text-slate-500 max-w-xs mx-auto">
                    No threads match your filters. Enjoy the quiet while it lasts.
                </p>
            </div>
        )
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                    {threads.length} Threads
                </span>
                <div className="flex items-center gap-4 text-xs">
                    <span className="text-slate-400 font-medium">Sort by:</span>
                    {['Urgency', 'Newest', 'Oldest', 'Days Open'].map((label) => {
                        const id = label.toLowerCase().replace(' ', '_')
                        return (
                            <button
                                key={id}
                                onClick={() => setSortBy(id)}
                                className={`font-semibold transition-colors ${sortBy === id ? 'text-blue-600' : 'text-slate-400 hover:text-slate-600'
                                    }`}
                            >
                                {label}
                            </button>
                        )
                    })}
                </div>
            </div>

            <div className="grid gap-3">
                {sortedThreads.map(thread => (
                    <ThreadCard
                        key={thread.id}
                        thread={thread}
                        onClick={() => onSelectThread(thread.id)}
                        isSelected={selectedThreadId === thread.id}
                    />
                ))}
            </div>
        </div>
    )
}
