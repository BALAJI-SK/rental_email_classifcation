import React, { useState } from 'react'
import ExportButton from './ExportButton'
import useVoice from '../hooks/useVoice'
import { fetchVoiceScript } from '../api'

const PROPERTIES = [
    { id: 'citynorth', name: 'Citynorth' },
    { id: 'highgate', name: 'Highgate' },
    { id: 'islington', name: 'Islington' },
    { id: 'canary_wharf', name: 'Canary Wharf' },
    { id: 'shoreditch', name: 'Shoreditch' },
]

const URGENCIES = [
    { id: 'critical', label: 'Critical', color: 'bg-red-500', icon: '🔴' },
    { id: 'high', label: 'High', color: 'bg-orange-500', icon: '🟠' },
    { id: 'medium', label: 'Medium', color: 'bg-yellow-500', icon: '🟡' },
    { id: 'low', label: 'Low', color: 'bg-green-500', icon: '🟢' },
]

export default function Sidebar({ threads, filters, setFilters, dashboardStats, analysisProgress, isOpen, onClose }) {
    const { speak, stop, isSpeaking } = useVoice()
    const [loadingVoice, setLoadingVoice] = useState(false)

    const toggleProperty = (id) => {
        const next = filters.properties.includes(id)
            ? filters.properties.filter(p => p !== id)
            : [...filters.properties, id]
        setFilters({ ...filters, properties: next })
    }

    const toggleUrgency = (id) => {
        const next = filters.urgencies.includes(id)
            ? filters.urgencies.filter(u => u !== id)
            : [...filters.urgencies, id]
        setFilters({ ...filters, urgencies: next })
    }

    const handleVoiceBrief = async () => {
        if (isSpeaking) {
            stop()
            return
        }
        setLoadingVoice(true)
        try {
            const { script } = await fetchVoiceScript()
            speak(script)
        } catch (err) {
            console.error(err)
        } finally {
            setLoadingVoice(false)
        }
    }

    const getThreadCount = (propId) => threads.filter(t => t.property_id === propId).length

    return (
        <>
            {/* Mobile Overlay */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-slate-900/60 z-40 lg:hidden backdrop-blur-sm"
                    onClick={onClose}
                />
            )}

            <aside className={`
                fixed inset-y-0 left-0 w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 z-50 transition-transform duration-300 lg:static lg:translate-x-0
                ${isOpen ? 'translate-x-0' : '-translate-x-full'}
            `}>
                <div className="p-6 flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold text-white tracking-tight">LETTE AI</h1>
                        <p className="text-[10px] uppercase tracking-widest text-slate-400 font-bold mt-1 opacity-60">Property Intelligence</p>
                    </div>
                    <button onClick={onClose} className="lg:hidden text-slate-500 hover:text-white font-bold text-xl">✕</button>
                </div>


                <nav className="flex-1 overflow-y-auto px-4 space-y-8 scrollbar-thin">
                    {/* Properties */}
                    <section>
                        <div className="flex items-center justify-between mb-3">
                            <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Properties</h3>
                            <button
                                onClick={() => setFilters({ ...filters, properties: filters.properties.length === PROPERTIES.length ? [] : PROPERTIES.map(p => p.id) })}
                                className="text-[10px] text-blue-400 font-bold hover:text-blue-300 transition-colors"
                            >
                                {filters.properties.length === PROPERTIES.length ? 'Clear' : 'All'}
                            </button>
                        </div>
                        <div className="space-y-1">
                            {PROPERTIES.map(p => (
                                <label key={p.id} className="flex items-center justify-between group cursor-pointer py-1.5 px-2 rounded-lg hover:bg-slate-800 transition-colors">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${filters.properties.includes(p.id) ? 'bg-blue-600 border-blue-600' : 'border-slate-700 bg-slate-800'}`}>
                                            {filters.properties.includes(p.id) && <span className="text-[10px] text-white">✓</span>}
                                        </div>
                                        <span className={`text-sm ${filters.properties.includes(p.id) ? 'text-slate-100' : 'text-slate-400'} transition-colors`}>{p.name}</span>
                                    </div>
                                    <span className="text-[10px] text-slate-500 font-medium">{getThreadCount(p.id)}</span>
                                    <input type="checkbox" className="hidden" checked={filters.properties.includes(p.id)} onChange={() => toggleProperty(p.id)} />
                                </label>
                            ))}
                        </div>
                    </section>

                    {/* Urgency */}
                    <section>
                        <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-3">Urgency</h3>
                        <div className="grid grid-cols-2 gap-2">
                            {URGENCIES.map(u => (
                                <button
                                    key={u.id}
                                    onClick={() => toggleUrgency(u.id)}
                                    className={`flex items-center gap-2 p-2 rounded-lg border transition-all ${filters.urgencies.includes(u.id)
                                        ? 'bg-slate-800 border-slate-700 ring-1 ring-slate-700'
                                        : 'bg-transparent border-transparent opacity-40 grayscale'
                                        }`}
                                >
                                    <span className="text-xs">{u.icon}</span>
                                    <span className="text-[10px] font-bold text-slate-200">{u.label}</span>
                                </button>
                            ))}
                        </div>
                    </section>

                    {/* Categories (simplified for space) */}
                    <section>
                        <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-3">Stats</h3>
                        <div className="space-y-2 bg-slate-950/50 rounded-xl p-3 border border-slate-800/50">
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-slate-500">Total Threads</span>
                                <span className="text-xs font-bold text-slate-300">{threads.length}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-slate-500">Unread</span>
                                <span className="text-xs font-bold text-blue-400">{threads.filter(t => t.is_unread).length}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-slate-500">Analysed</span>
                                <span className="text-xs font-bold text-green-400">{threads.filter(t => t.is_analysed).length}</span>
                            </div>
                        </div>
                    </section>
                </nav>

                <div className="p-4 space-y-3 bg-slate-950/30 border-t border-slate-800">
                    <button
                        onClick={handleVoiceBrief}
                        disabled={loadingVoice}
                        className={`w-full h-10 rounded-lg flex items-center justify-center gap-2 font-bold text-sm transition-all ${isSpeaking
                            ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                            : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                            }`}
                    >
                        {loadingVoice ? (
                            <span className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                        ) : isSpeaking ? (
                            <>
                                <div className="flex gap-0.5 items-end h-3">
                                    <div className="w-1 bg-blue-400 animate-pulse" style={{ height: '60%' }} />
                                    <div className="w-1 bg-blue-400 animate-pulse" style={{ height: '100%', animationDelay: '0.2s' }} />
                                    <div className="w-1 bg-blue-400 animate-pulse" style={{ height: '40%', animationDelay: '0.4s' }} />
                                </div>
                                Stop Brief
                            </>
                        ) : (
                            <>
                                <span>🔊</span>
                                Voice Brief
                            </>
                        )}
                    </button>
                    <ExportButton filters={filters} />
                </div>
            </aside>
        </>
    )
}

