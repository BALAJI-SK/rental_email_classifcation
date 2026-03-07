import React from 'react'

export default function ContactCard({ contact }) {
    if (!contact) return null

    const isUnknown = !contact.phone || !contact.unit
    const sentimentMap = {
        positive: '😊',
        neutral: '😐',
        negative: '😠',
        angry: '😡',
    }

    const typeColorMap = {
        tenant: 'bg-blue-100 text-blue-700',
        contractor: 'bg-purple-100 text-purple-700',
        prospect: 'bg-green-100 text-green-700',
        legal: 'bg-red-100 text-red-700',
    }

    return (
        <div className="bg-slate-50 rounded-2xl p-6 border border-slate-100 transition-all hover:shadow-md">
            <div className="flex items-start justify-between mb-6">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xl font-bold shadow-lg shadow-blue-100">
                        {contact.name.charAt(0)}
                    </div>
                    <div>
                        <h4 className="font-bold text-slate-900">{contact.name}</h4>
                        <div className="flex items-center gap-2 mt-1">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${typeColorMap[contact.type] || 'bg-slate-200 text-slate-600'}`}>
                                {contact.type}
                            </span>
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${isUnknown ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'}`}>
                                {isUnknown ? '⚠ Details needed' : '✓ Known'}
                            </span>
                        </div>
                    </div>
                </div>
                <div className="flex flex-col items-center">
                    <span className="text-2xl" title={`${contact.sentiment} sentiment`}>{sentimentMap[contact.sentiment] || '😐'}</span>
                    <span className="text-[10px] font-bold text-slate-400 mt-1 uppercase">Sentiment</span>
                </div>
            </div>

            {isUnknown && (
                <div className="bg-orange-50/50 border border-orange-100 rounded-lg p-3 mb-6 flex items-center gap-3">
                    <span className="text-lg">📋</span>
                    <div>
                        <p className="text-[10px] font-bold text-orange-800 uppercase tracking-widest leading-none mb-1">Missing Profile Info</p>
                        <p className="text-xs text-orange-700/80">Missing: {[!contact.phone && 'phone', !contact.unit && 'unit'].filter(Boolean).join(', ')}</p>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-2 gap-y-4 gap-x-8">
                {[
                    { label: 'Email', value: contact.email, icon: '✉️' },
                    { label: 'Phone', value: contact.phone || 'Unknown', icon: '📞' },
                    { label: 'Unit', value: contact.unit || 'Not set', icon: '🏠' },
                    { label: 'Property', value: contact.property_name, icon: '🏢' },
                ].map((item, i) => (
                    <div key={i}>
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">{item.label}</div>
                        <div className="text-xs font-semibold text-slate-700 truncate flex items-center gap-2">
                            <span className="opacity-50 grayscale">{item.icon}</span>
                            {item.value}
                        </div>
                    </div>
                ))}
            </div>

            <div className="mt-8 pt-6 border-t border-slate-200/60 flex items-center justify-between">
                <div className="flex gap-4">
                    <div className="text-center">
                        <div className="text-xs font-bold text-slate-900">{contact.total_messages || 0}</div>
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total</div>
                    </div>
                    <div className="text-center border-l border-slate-200/60 pl-4">
                        <div className="text-xs font-bold text-slate-900">{contact.open_threads || 0}</div>
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Open</div>
                    </div>
                </div>
                <button className="text-xs font-bold text-blue-600 hover:text-blue-700 hover:underline transition-all">
                    View history →
                </button>
            </div>
        </div>
    )
}
