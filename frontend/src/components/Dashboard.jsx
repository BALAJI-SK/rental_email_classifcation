import React, { useState } from 'react'
import ThreadList from './ThreadList'
import PatternAlerts from './PatternAlerts'
import MorningBrief from './MorningBrief'

export default function Dashboard({ stats, threads, filters, patterns, morningBrief, onSelectThread, selectedThreadId }) {
    const [activeTab, setActiveTab] = useState('inbox')

    // Filter threads
    const filteredThreads = threads.filter(t => {
        // Property filter
        if (filters.properties.length > 0 && !filters.properties.includes(t.property_id)) return false
        // Urgency filter
        if (filters.urgencies.length > 0 && !filters.urgencies.includes(t.urgency)) return false

        // Tab filtering
        if (activeTab === 'drafts') return t.status === 'draft_ready'
        if (activeTab === 'procurement') return t.category && t.category.startsWith('maintenance') && t.procurement_job_id
        if (activeTab === 'auto_replies') return t.was_auto_replied

        return true
    })

    const counts = {
        drafts: threads.filter(t => t.status === 'draft_ready').length,
        procurement: threads.filter(t => t.category && t.category.startsWith('maintenance') && t.procurement_job_id).length,
        auto_replies: threads.filter(t => t.was_auto_replied).length,
    }

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            {/* Stat Cards */}
            <div className="grid grid-cols-4 gap-6">
                <StatCard
                    label="Total Threads"
                    value={stats?.total_threads || 0}
                    unit="threads"
                    icon="📥"
                />
                <StatCard
                    label="Critical"
                    value={stats?.critical_count || 0}
                    icon="🚨"
                    color="text-red-600 bg-red-50"
                />
                <StatCard
                    label="Unread"
                    value={stats?.unread_count || 0}
                    icon="🔵"
                    color="text-blue-600 bg-blue-50"
                />
                <StatCard
                    label="Pattern Alerts"
                    value={patterns.length}
                    icon="🧠"
                    color="text-purple-600 bg-purple-50"
                />
            </div>

            {/* Tabs */}
            <div className="border-b border-slate-200">
                <div className="flex gap-8">
                    <Tab
                        id="inbox"
                        label="Inbox"
                        active={activeTab === 'inbox'}
                        onClick={setActiveTab}
                    />
                    <Tab
                        id="drafts"
                        label="Drafts"
                        count={counts.drafts}
                        active={activeTab === 'drafts'}
                        onClick={setActiveTab}
                    />
                    <Tab
                        id="procurement"
                        label="Procurement"
                        count={counts.procurement}
                        active={activeTab === 'procurement'}
                        onClick={setActiveTab}
                    />
                    <Tab
                        id="auto_replies"
                        label="Auto-Replies"
                        count={counts.auto_replies}
                        active={activeTab === 'auto_replies'}
                        onClick={setActiveTab}
                    />
                </div>
            </div>

            <div className="space-y-6">
                {patterns.length > 0 && <PatternAlerts patterns={patterns} />}
                {morningBrief && <MorningBrief brief={morningBrief} />}

                <ThreadList
                    threads={filteredThreads}
                    onSelectThread={onSelectThread}
                    selectedThreadId={selectedThreadId}
                />
            </div>
        </div>
    )
}

function StatCard({ label, value, unit, icon, color = "bg-white" }) {
    return (
        <div className={`p-6 rounded-2xl border border-slate-100 shadow-sm ${color}`}>
            <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold uppercase tracking-widest opacity-60">{label}</span>
                <span className="text-xl">{icon}</span>
            </div>
            <div className="flex items-baseline gap-1">
                <span className="text-3xl font-bold tracking-tight">{value}</span>
                {unit && <span className="text-xs font-medium opacity-50">{unit}</span>}
            </div>
        </div>
    )
}

function Tab({ id, label, count, active, onClick }) {
    return (
        <button
            onClick={() => onClick(id)}
            className={`pb-4 px-1 text-sm font-semibold transition-all relative ${active ? 'text-blue-600' : 'text-slate-500 hover:text-slate-700'
                }`}
        >
            <div className="flex items-center gap-2">
                {label}
                {count > 0 && (
                    <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${active ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'}`}>
                        {count}
                    </span>
                )}
            </div>
            {active && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full" />}
        </button>
    )
}
