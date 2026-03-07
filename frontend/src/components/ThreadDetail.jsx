import React, { useState, useEffect } from 'react'
import UrgencyBadge from './UrgencyBadge'
import CategoryBadge from './CategoryBadge'
import MessageBubble from './MessageBubble'
import ActionCard from './ActionCard'
import ProcurementPanel from './ProcurementPanel'
import ContactCard from './ContactCard'
import * as api from '../api'

export default function ThreadDetail({ thread, onClose, onUpdate }) {
    const [draft, setDraft] = useState(thread.ai_draft || '')
    const [status, setStatus] = useState(thread.status || 'open')
    const [isAnalysing, setIsAnalysing] = useState(false)

    useEffect(() => {
        setDraft(thread.ai_draft || '')
        setStatus(thread.status || 'open')
    }, [thread])

    const handleStatusChange = async (newStatus) => {
        setStatus(newStatus)
        try {
            const updated = await api.updateThread(thread.id, { status: newStatus })
            onUpdate(updated)
        } catch (err) {
            console.error(err)
        }
    }

    const handleAnalyse = async () => {
        setIsAnalysing(true)
        try {
            const updated = await api.triggerAnalysis(thread.id)
            onUpdate(updated)
        } catch (err) {
            console.error(err)
        } finally {
            setIsAnalysing(false)
        }
    }

    const copyToClipboard = () => {
        navigator.clipboard.writeText(draft)
        // could add a toast here
    }

    const handleSend = async () => {
        try {
            const updated = await api.updateThread(thread.id, { status: 'resolved', ai_draft: draft })
            onUpdate(updated)
            onClose()
        } catch (err) {
            console.error(err)
        }
    }

    return (
        <div className="fixed inset-y-0 right-0 w-[480px] bg-white shadow-2xl z-40 border-l border-slate-100 flex flex-col transform transition-transform duration-300 animate-in slide-in-from-right">
            {/* Header */}
            <div className="p-6 border-b border-slate-100 shrink-0">
                <div className="flex justify-between items-start mb-4">
                    <div className="flex flex-wrap gap-2 pr-8">
                        <UrgencyBadge level={thread.urgency} />
                        <CategoryBadge category={thread.category} />
                        <span className="px-1.5 py-0.5 rounded-full text-[10px] uppercase font-bold tracking-wider bg-slate-100 text-slate-600">
                            {thread.property_name}
                        </span>
                        {thread.unit && (
                            <span className="px-1.5 py-0.5 rounded-full text-[10px] uppercase font-bold tracking-wider bg-slate-100 text-slate-400">
                                Unit {thread.unit}
                            </span>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-400 transition-colors"
                    >
                        ✕
                    </button>
                </div>

                <h2 className="text-xl font-bold text-slate-900 leading-tight mb-4">{thread.subject}</h2>

                <div className="flex items-center gap-4">
                    <select
                        value={status}
                        onChange={(e) => handleStatusChange(e.target.value)}
                        className="text-xs font-bold uppercase tracking-wider bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="open">Open</option>
                        <option value="in_progress">In Progress</option>
                        <option value="snoozed">Snoozed</option>
                        <option value="resolved">Resolved</option>
                        <option value="escalated">Escalated</option>
                    </select>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                        Last active {thread.last_message_at_relative} ago
                    </span>
                </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto scrollbar-thin p-6 space-y-8">

                {/* AI Analysis Section */}
                <section className="bg-blue-50/50 rounded-2xl p-5 border border-blue-100 relative">
                    <div className="flex items-center gap-2 mb-4 text-[10px] font-bold text-blue-600 uppercase tracking-widest">
                        <span>✨</span> AI Analysis
                    </div>

                    {thread.is_analysed ? (
                        <>
                            <p className="text-sm text-slate-700 leading-relaxed mb-4">{thread.ai_summary}</p>

                            <div className="space-y-2 mb-6">
                                <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Urgency Reasons</h4>
                                <ul className="space-y-1.5">
                                    {Array.isArray(thread.urgency_reasons) && thread.urgency_reasons.map((reason, i) => (
                                        <li key={i} className="flex gap-2 text-xs text-slate-600">
                                            <span className="text-blue-400">•</span>
                                            {reason}
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {Array.isArray(thread.risk_flags) && thread.risk_flags.length > 0 && (
                                <div className="space-y-2 mb-6">
                                    {thread.risk_flags.map((flag, i) => (
                                        <div key={i} className="bg-red-50 border border-red-100 rounded-lg p-3 flex items-center gap-3">
                                            <span className="text-lg">⚠️</span>
                                            <span className="text-xs font-semibold text-red-900">{flag}</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <footer className="text-[10px] text-slate-400 font-medium">
                                Analysed {thread.analysed_at_relative} ago
                            </footer>
                        </>
                    ) : (
                        <div className="py-4 text-center">
                            <p className="text-sm text-slate-500 italic mb-4">This thread hasn't been analysed yet.</p>
                            <button
                                onClick={handleAnalyse}
                                disabled={isAnalysing}
                                className="w-full h-10 bg-blue-600 text-white rounded-xl font-bold text-xs uppercase tracking-widest hover:bg-blue-700 transition-all disabled:opacity-50"
                            >
                                {isAnalysing ? 'Analysing...' : 'Analyse Now'}
                            </button>
                        </div>
                    )}
                </section>

                {/* Escalation Timeline */}
                {thread.escalation_history && thread.escalation_history.length > 0 && (
                    <section>
                        <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-4">Escalation History</h3>
                        <div className="space-y-4 pl-4 border-l-2 border-slate-100">
                            {thread.escalation_history.map((node, i) => (
                                <div key={i} className="relative">
                                    <div className="absolute -left-[21px] top-1 w-3 h-3 rounded-full border-2 border-white bg-slate-300" />
                                    <div className="text-[10px] font-bold text-slate-400 mb-1 uppercase">{node.timestamp_relative} ago</div>
                                    <div className="text-xs font-semibold text-slate-700">
                                        {node.old_level} → <span className="text-red-600 uppercase italic font-bold">{node.new_level}</span>
                                    </div>
                                    <p className="text-xs text-slate-500 mt-1 italic">"{node.reason}"</p>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Contact Info */}
                <section>
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-4">Sender Details</h3>
                    <ContactCard contact={thread.contact_profile} />
                </section>

                {/* Conversation */}
                <section>
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-6">Conversation ({thread.messages?.length || 0})</h3>
                    <div className="space-y-4">
                        {(thread.messages || []).map((msg, i) => (
                            <MessageBubble key={i} message={msg} />
                        ))}
                    </div>
                </section>

                {/* Recommended Actions */}
                {Array.isArray(thread.recommended_actions) && thread.recommended_actions.length > 0 && (
                    <section>
                        <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-4">Recommended Actions</h3>
                        <div className="space-y-3">
                            {thread.recommended_actions.map((action, i) => (
                                <ActionCard key={i} action={action} index={i} />
                            ))}
                        </div>
                    </section>
                )}

                {/* Procurement */}
                {thread.procurement_job && (
                    <ProcurementPanel job={thread.procurement_job} />
                )}

                {/* Draft Response */}
                <section className="bg-slate-900 rounded-3xl p-6 text-white overflow-hidden relative">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-blue-600 rounded-full blur-[80px] opacity-20 -mr-16 -mt-16" />

                    <div className="flex items-center justify-between mb-4 relative z-10">
                        <div className="flex items-center gap-2 text-[10px] font-bold text-blue-400 uppercase tracking-widest">
                            <span>✍️</span> AI Drafted Response
                        </div>
                        <button className="text-[10px] font-bold uppercase tracking-widest text-slate-400 hover:text-white transition-colors">
                            Edit ✎
                        </button>
                    </div>

                    <textarea
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        className="w-full h-48 bg-slate-800/50 border border-slate-700 rounded-xl p-4 text-sm leading-relaxed text-slate-200 outline-none focus:ring-1 focus:ring-blue-500 transition-all resize-none mb-6 relative z-10"
                        placeholder="Type or refine the response..."
                    />

                    <div className="flex gap-3 relative z-10">
                        <button
                            onClick={handleSend}
                            className="flex-1 h-11 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold text-xs uppercase tracking-widest transition-all shadow-lg shadow-blue-900/40"
                        >
                            Approve & Send
                        </button>
                        <button
                            onClick={copyToClipboard}
                            className="px-4 h-11 bg-slate-800 hover:bg-slate-700 rounded-xl font-bold text-xs transition-colors"
                            title="Copy to clipboard"
                        >
                            📋
                        </button>
                        <button
                            onClick={() => setDraft(thread.ai_draft || '')}
                            className="px-4 h-11 bg-slate-800 hover:bg-slate-700 rounded-xl font-bold text-xs transition-colors"
                            title="Regenerate"
                        >
                            ↻
                        </button>
                    </div>
                </section>
            </div>
        </div>
    )
}
