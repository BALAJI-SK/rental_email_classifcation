import React from 'react'

const CONFIG = {
    maintenance_emergency: { icon: '🔧', color: 'bg-red-100 text-red-700', label: 'Emergency' },
    maintenance_urgent: { icon: '🔧', color: 'bg-orange-100 text-orange-700', label: 'Urgent' },
    maintenance_routine: { icon: '🔧', color: 'bg-slate-100 text-slate-700', label: 'Routine' },
    lease: { icon: '📄', color: 'bg-blue-100 text-blue-700', label: 'Lease' },
    payment: { icon: '💰', color: 'bg-green-100 text-green-700', label: 'Payment' },
    complaint: { icon: '😤', color: 'bg-orange-100 text-orange-700', label: 'Complaint' },
    legal: { icon: '⚖️', color: 'bg-red-100 text-red-700', label: 'Legal' },
    prospect: { icon: '🏠', color: 'bg-purple-100 text-purple-700', label: 'Prospect' },
    contractor: { icon: '🏗️', color: 'bg-teal-100 text-teal-700', label: 'Contractor' },
    system_alert: { icon: '⚙️', color: 'bg-slate-100 text-slate-700', label: 'System' },
    landlord: { icon: '🏢', color: 'bg-indigo-100 text-indigo-700', label: 'Landlord' },
}

export default function CategoryBadge({ category }) {
    const config = CONFIG[category] || { icon: '📁', color: 'bg-slate-100 text-slate-700', label: category }

    return (
        <div className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-bold flex items-center gap-1 ${config.color}`}>
            <span>{config.icon}</span>
            {config.label}
        </div>
    )
}
