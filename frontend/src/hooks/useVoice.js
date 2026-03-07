import { useState, useCallback, useRef } from 'react'

export default function useVoice() {
  const [isSpeaking, setIsSpeaking] = useState(false)
  const utteranceRef = useRef(null)

  const speak = useCallback((text) => {
    if (!window.speechSynthesis) return

    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(text)
    utteranceRef.current = utterance

    // Pick a natural English voice
    const voices = window.speechSynthesis.getVoices()
    const preferred = voices.find(v =>
      v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Premium') || v.name.includes('Enhanced'))
    ) || voices.find(v => v.lang === 'en-GB' || v.lang === 'en-IE') || voices.find(v => v.lang.startsWith('en'))

    if (preferred) utterance.voice = preferred
    utterance.rate = 0.95
    utterance.pitch = 1.0

    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)

    window.speechSynthesis.speak(utterance)
  }, [])

  const stop = useCallback(() => {
    window.speechSynthesis?.cancel()
    setIsSpeaking(false)
  }, [])

  return { speak, stop, isSpeaking }
}
