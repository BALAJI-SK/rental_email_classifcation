import React, { useState } from 'react'
import { exportExcel } from '../api'

const OPTIONS = [
    { id: 'open_issues', label: 'Open Issues', icon: '📝' },
    { id: 'tenant_contacts', label: 'Tenant Contacts', icon: '👥' },
    { id: 'overdue_responses', label: 'Overdue Responses', icon: '⏰' },
    { id: 'property_report', label: 'Property Report', icon: '📊' },
]

export default function ExportButton({ filters }) {
    const [open, setOpen] = useState(false)
    const [loading, setLoading] = useState(null)

    const handleExport = async (type) => {
        setLoading(type)
        setOpen(false)
        try {
            await exportExcel(type, filters)
        } catch (err) {
            console.error('Export failed', err)
        } finally {
            setLoading(null)
        }
    }

    return (
        <div className="relative w-full">
            <button
                onClick={() => setOpen(!open)}
                className="w-full h-10 px-4 flex items-center justify-between gap-2 bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 rounded-lg font-medium transition-colors"
            >
                <div className="flex items-center gap-2">
                    <span>📤</span>
                    Export
                </div>
                <span className="text-[10px] opacity-50">▾</span>
            </button>

            {open && (
                <>
                    <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
                    <div className="absolute bottom-full left-0 mb-2 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-2xl z-50 overflow-hidden py-1">
                        {OPTIONS.map(opt => (
                            <button
                                key={opt.id}
                                onClick={() => handleExport(opt.id)}
                                disabled={loading !== null}
                                className="w-full text-left px-4 py-2.5 hover:bg-slate-700 flex items-center gap-3 text-sm text-slate-300 transition-colors disabled:opacity-50"
                            >
                                {loading === opt.id ? (
                                    <span className="animate-spin">⏳</span>
                                ) : (
                                    <span>{opt.icon}</span>
                                )}
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </>
            )}
        </div>
    )
}
