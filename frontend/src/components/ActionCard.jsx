import React, { useState } from 'react'

export default function ActionCard({ action, index }) {
    const [done, setDone] = useState(false)

    const deadlineStyles = {
        immediately: 'bg-red-100 text-red-700',
        today: 'bg-orange-100 text-orange-700',
        '48_hours': 'bg-yellow-100 text-yellow-700',
    }

    const deadlineLabel = {
        immediately: 'Immediately',
        today: 'Today',
        '48_hours': 'Within 48 hours',
    }

    return (
        <div className={`p-4 rounded-xl border transition-all duration-300 ${done ? 'bg-slate-50 border-slate-100 opacity-60' : 'bg-white border-slate-200'
            }`}>
            <div className="flex items-start gap-4">
                <label className="shrink-0 mt-1 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={done}
                        onChange={() => setDone(!done)}
                        className="w-5 h-5 rounded-full border-2 border-slate-300 text-blue-600 focus:ring-0 cursor-pointer"
                    />
                </label>

                <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1 gap-2">
                        <h4 className={`text-sm font-bold ${done ? 'line-through text-slate-400' : 'text-slate-900'}`}>
                            <span className="opacity-40 mr-2">{index + 1}.</span>
                            {action.title}
                        </h4>
                        <span className={`shrink-0 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${deadlineStyles[action.deadline_type] || 'bg-slate-100'}`}>
                            {deadlineLabel[action.deadline_type] || action.deadline_type}
                        </span>
                    </div>
                    <p className={`text-xs leading-relaxed ${done ? 'text-slate-300' : 'text-slate-500'}`}>
                        {action.reasoning}
                    </p>
                </div>
            </div>
        </div>
    )
}
