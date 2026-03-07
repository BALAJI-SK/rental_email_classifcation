import React, { useState, useEffect, useRef } from 'react'
import { sendChat } from '../api'

export default function SearchBar({ onSearch }) {
    const [query, setQuery] = useState('')
    const [aiResponse, setAiResponse] = useState(null)
    const [loading, setLoading] = useState(false)
    const timeoutRef = useRef(null)

    useEffect(() => {
        // Debounced search for filtering
        if (timeoutRef.current) clearTimeout(timeoutRef.current)
        timeoutRef.current = setTimeout(() => {
            onSearch(query)
        }, 300)
        return () => clearTimeout(timeoutRef.current)
    }, [query, onSearch])

    const handleKeyDown = async (e) => {
        if (e.key === 'Enter' && query.length > 5) {
            const isNaturalLanguage = query.split(' ').length > 2 || query.includes('?')
            if (isNaturalLanguage) {
                setLoading(true)
                try {
                    const res = await sendChat(query)
                    setAiResponse(res)
                } catch (err) {
                    console.error(err)
                } finally {
                    setLoading(false)
                }
            }
        }
    }

    return (
        <div className="relative flex-1 max-w-2xl">
            <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Search threads or ask: 'show me urgent issues at Citynorth'"
                    className="w-full h-10 pl-10 pr-4 bg-slate-100 border-none rounded-lg text-sm focus:ring-2 focus:ring-blue-500 transition-all outline-none"
                />
                {loading && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                        <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                )}
            </div>

            {aiResponse && (
                <>
                    <div className="fixed inset-0 z-40" onClick={() => setAiResponse(null)} />
                    <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-slate-200 rounded-xl shadow-2xl z-50 p-4 animate-in fade-in slide-in-from-top-2">
                        <div className="flex items-center gap-2 mb-2 text-[10px] font-bold text-blue-600 uppercase tracking-widest">
                            <span>🧠</span> AI Assistant
                        </div>
                        <div className="text-sm text-slate-700 leading-relaxed">
                            {aiResponse}
                        </div>
                        <button
                            onClick={() => setAiResponse(null)}
                            className="mt-4 text-xs font-semibold text-slate-400 hover:text-slate-600"
                        >
                            Close
                        </button>
                    </div>
                </>
            )}
        </div>
    )
}
