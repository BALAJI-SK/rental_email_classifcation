import React from 'react'

export default function ProcurementPanel({ job }) {
    if (!job) return null

    const steps = [
        { id: 'requesting', label: 'Requesting Quotes' },
        { id: 'collecting', label: 'Collecting' },
        { id: 'comparing', label: 'Comparing' },
        { id: 'negotiating', label: 'Negotiating' },
        { id: 'booked', label: 'Booked' },
    ]

    const currentStepIndex = steps.findIndex(s => s.id === job.status)
    const isEmergency = job.is_emergency

    return (
        <div className="mt-8 pt-8 border-t border-slate-100">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400">Procurement Process</h3>
                {isEmergency && (
                    <span className="px-2 py-1 bg-red-600 text-white rounded text-[10px] font-bold animate-pulse">
                        ⚡ EMERGENCY FAST-TRACK
                    </span>
                )}
            </div>

            {isEmergency ? (
                <div className="p-4 bg-red-50 rounded-xl border border-red-100 flex items-center gap-4">
                    <div className="text-2xl">👷</div>
                    <div className="flex-1">
                        <h4 className="text-sm font-bold text-red-900">Assigned: {job.assigned_contractor}</h4>
                        <p className="text-xs text-red-700 opacity-80">Emergency protocol triggered. Booking confirmed for today.</p>
                    </div>
                </div>
            ) : (
                <>
                    {/* Progress Bar */}
                    <div className="flex justify-between mb-8 relative px-2">
                        <div className="absolute top-2.5 left-8 right-8 h-0.5 bg-slate-100 -z-10" />
                        <div
                            className="absolute top-2.5 left-8 h-0.5 bg-blue-600 -z-10 transition-all duration-1000"
                            style={{ width: `${(currentStepIndex / (steps.length - 1)) * (100 - 16)}%` }}
                        />
                        {steps.map((step, i) => {
                            const isActive = i <= currentStepIndex
                            return (
                                <div key={step.id} className="flex flex-col items-center gap-2">
                                    <div className={`w-5 h-5 rounded-full border-4 transition-all duration-500 ${isActive ? 'bg-blue-600 border-blue-100' : 'bg-white border-slate-100'
                                        }`} />
                                    <span className={`text-[10px] font-bold tracking-tight text-center max-w-[60px] ${isActive ? 'text-slate-900' : 'text-slate-400'
                                        }`}>
                                        {step.label}
                                    </span>
                                </div>
                            )
                        })}
                    </div>

                    {/* Quotes Table */}
                    {job.quotes && job.quotes.length > 0 && (
                        <div className="bg-slate-50 rounded-2xl border border-slate-100 overflow-hidden">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-slate-100/50">
                                        <th className="px-4 py-3 text-[10px] uppercase font-bold text-slate-500">Contractor</th>
                                        <th className="px-4 py-3 text-[10px] uppercase font-bold text-slate-500">Price</th>
                                        <th className="px-4 py-3 text-[10px] uppercase font-bold text-slate-500 text-center">Rating</th>
                                        <th className="px-4 py-3 text-[10px] uppercase font-bold text-slate-500 text-right">Action</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {job.quotes.map((quote, i) => (
                                        <tr key={i} className={`text-xs hover:bg-white transition-colors ${quote.is_recommended ? 'bg-green-50/50 ring-1 ring-inset ring-green-100' : ''}`}>
                                            <td className="px-4 py-3">
                                                <div className="font-bold text-slate-900">{quote.contractor}</div>
                                                <div className="text-[10px] text-slate-500">{quote.availability}</div>
                                            </td>
                                            <td className="px-4 py-3 font-semibold text-slate-900">£{quote.price}</td>
                                            <td className="px-4 py-3 text-center">
                                                <div className="flex items-center justify-center gap-1">
                                                    <span className="text-yellow-500">★</span>
                                                    <span className="font-bold">{quote.rating}</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 text-right">
                                                <button className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider transition-all ${quote.is_recommended ? 'bg-green-600 text-white hover:bg-green-700' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                                                    }`}>
                                                    {job.status === 'comparing' ? 'Book' : 'View'}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}
