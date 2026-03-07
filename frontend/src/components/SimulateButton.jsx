import React, { useState } from 'react'

const SCENARIOS = [
    { id: 'tenant_followup', label: 'Tenant Follow-up', icon: '👤' },
    { id: 'new_prospect', label: 'New Prospect', icon: '🏠' },
    { id: 'emergency', label: 'Emergency', icon: '🚨' },
    { id: 'contractor_reply', label: 'Contractor Reply', icon: '🏗️' },
    { id: 'unknown_sender', label: 'Unknown Sender', icon: '❓' },
]

export default function SimulateButton({ onSimulate }) {
    const [open, setOpen] = useState(false)

    const handleSimulate = async (id) => {
        setOpen(false)
        try {
            await onSimulate(id)
        } catch (err) {
            console.error('Simulation failed', err)
        }
    }

    return (
        <div className="relative">
            <button
                onClick={() => setOpen(!open)}
                className="h-10 px-4 flex items-center gap-2 bg-slate-100 border border-slate-200 text-slate-700 hover:bg-slate-200 rounded-lg font-medium transition-colors"
            >
                <span>🎭</span>
                Simulate
                <span className="text-[10px] ml-1 opacity-50">▾</span>
            </button>

            {open && (
                <>
                    <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
                    <div className="absolute right-0 mt-2 w-56 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden py-1">
                        <div className="px-3 py-2 text-[10px] uppercase tracking-wider font-bold text-slate-400 border-b border-slate-50">
                            Pick a Demo Scenario
                        </div>
                        {SCENARIOS.map(s => (
                            <button
                                key={s.id}
                                onClick={() => handleSimulate(s.id)}
                                className="w-full text-left px-4 py-2.5 hover:bg-slate-50 flex items-center gap-3 text-sm text-slate-700 transition-colors"
                            >
                                <span className="text-lg">{s.icon}</span>
                                {s.label}
                            </button>
                        ))}
                    </div>
                </>
            )}
        </div>
    )
}
