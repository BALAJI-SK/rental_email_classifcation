import React, { useState, useEffect } from 'react'

export default function AnalyseButton({ progress, onAnalyse }) {
    const [complete, setComplete] = useState(false)

    useEffect(() => {
        if (progress === null && complete === false) {
            // Check if we just finished
        }
    }, [progress])

    const handleClick = async () => {
        try {
            await onAnalyse()
        } catch (err) {
            console.error(err)
        }
    }

    if (progress) {
        const percent = Math.round((progress.current / progress.total) * 100)
        return (
            <div className="relative h-10 w-48 bg-slate-100 rounded-lg overflow-hidden border border-blue-200">
                <div
                    className="absolute inset-0 bg-blue-500 transition-all duration-500"
                    style={{ width: `${percent}%` }}
                />
                <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-blue-900 mix-blend-multiply">
                    Analysing {progress.current}/{progress.total}...
                </div>
            </div>
        )
    }

    return (
        <button
            onClick={handleClick}
            className={`h-10 px-4 rounded-lg font-semibold flex items-center gap-2 transition-all ${complete
                    ? 'bg-green-500 text-white shadow-green-100 shadow-lg'
                    : 'bg-blue-600 text-white hover:bg-blue-700 shadow-blue-100 shadow-lg'
                }`}
        >
            {complete ? (
                <>
                    <span>✓</span>
                    Analysis Complete
                </>
            ) : (
                <>
                    <span>⚡</span>
                    Analyse All
                </>
            )}
        </button>
    )
}
