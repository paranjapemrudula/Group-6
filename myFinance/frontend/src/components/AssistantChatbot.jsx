import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import botAvatar from '../assets/assistant-bot.svg'

function buildLocalFallbackAnswer(questionText) {
  const text = String(questionText || '').toLowerCase()

  if (text.includes('market') && text.includes('trend')) {
    return 'I could not fetch the live market feed right now, but the right answer here should come from market overview and latest headlines. Please retry once, and if the backend is running, I will answer with current trend, key stocks, and recent market news.'
  }

  if (text.includes('sentiment') || text.includes('bullish') || text.includes('bearish')) {
    return 'I could not load sentiment data right now. This answer should normally use recent company and portfolio news sentiment to tell you whether signals are positive, negative, or neutral.'
  }

  if (text.includes('sector')) {
    return 'I could not load sector data right now. This answer should normally use your sector database and mapped stocks to explain which sectors are strong and which stocks belong to them.'
  }

  if (text.includes('quality') || text.includes('pe') || text.includes('cluster')) {
    return 'I could not load quality analysis right now. This answer should normally use your quality view, P/E comparison, and clustering data to explain stronger and weaker stock groups.'
  }

  if (
    text.includes('portfolio') ||
    text.includes('profit') ||
    text.includes('loss') ||
    text.includes('return') ||
    text.includes('holding')
  ) {
    return 'I could not load your portfolio analysis right now. This answer should normally use your saved holdings, buy prices, quantities, and live prices to calculate returns, profit or loss, and portfolio summary.'
  }

  if (text.includes('buy') || text.includes('sell') || text.includes('hold') || text.includes('recommend')) {
    return 'I could not load recommendation data right now. This answer should normally use profitability, sentiment, price direction, and diversification signals to suggest buy, hold, sell, or rebalance.'
  }

  if (text.includes('stock') || text.includes('price') || text.includes('quote')) {
    return 'I could not load stock quote data right now. This answer should normally use live stock price, P/E ratio, and 52-week range for the symbol you asked about.'
  }

  return 'I could not reach the full chatbot service right now, but I am still set up for finance questions about your portfolio, market trend, sectors, sentiment, quality, and recommendations. Please try the same question again once the backend finishes responding.'
}

function shouldReplaceWithFallback(messageText) {
  const text = String(messageText || '').trim().toLowerCase()
  if (!text) return true

  const genericPatterns = [
    'i am sorry, but i could not respond right now',
    'please try again in a moment',
    'network error',
    'failed to fetch',
    'request failed',
    'internal server error',
    'could not generate a response right now',
    'the chatbot hit a temporary problem',
  ]

  return genericPatterns.some((pattern) => text.includes(pattern))
}

function AssistantChatbot() {
  const bodyRef = useRef(null)
  const [isOpen, setIsOpen] = useState(false)
  const [input, setInput] = useState('')
  const [pending, setPending] = useState(false)
  const [errorText, setErrorText] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text:
        'Hello. I am here to help with stocks, market news, and your portfolio. Please ask anything related to finance in simple words.',
    },
  ])

  useEffect(() => {
    if (!isOpen || !bodyRef.current) return
    bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [messages, isOpen])

  const sendQuestion = async (questionText) => {
    const question = questionText.trim()
    if (!question || pending) return

    const nextUserMessage = { role: 'user', text: question }
    const history = messages.map((item) => ({
      role: item.role,
      text: item.text,
    }))

    setMessages((prev) => [...prev, nextUserMessage])
    setInput('')
    setPending(true)
    setErrorText('')

    try {
      const response = await api.post('/api/chatbot/', {
        question,
        history,
      })

      const backendAnswer = response.data?.answer
      const finalAnswer = shouldReplaceWithFallback(backendAnswer)
        ? buildLocalFallbackAnswer(question)
        : backendAnswer

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: finalAnswer || buildLocalFallbackAnswer(question),
        },
      ])
    } catch (error) {
      const backendMessage =
        error?.response?.data?.answer ||
        error?.response?.data?.detail ||
        error?.message
      const finalMessage = shouldReplaceWithFallback(backendMessage)
        ? buildLocalFallbackAnswer(question)
        : backendMessage
      setErrorText(shouldReplaceWithFallback(backendMessage) ? '' : backendMessage)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: finalMessage,
        },
      ])
    } finally {
      setPending(false)
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    await sendQuestion(input)
  }

  return (
    <div className="assistant-widget">
      {isOpen ? (
        <div className="assistant-panel">
          <div className="assistant-head">
            <div className="assistant-head-left">
              <img src={botAvatar} alt="MyFinance chatbot" className="assistant-avatar" />
              <div>
                <strong>MyFinance Chatbot</strong>
                <p>Finance-only, privacy-aware assistant</p>
              </div>
            </div>
            <button type="button" onClick={() => setIsOpen(false)} aria-label="Close chatbot">
              ×
            </button>
          </div>

          <div ref={bodyRef} className="assistant-body">
            {messages.map((msg, index) => (
              <div key={`${msg.role}-${index}`} className={`assistant-msg assistant-${msg.role}`}>
                <p>{msg.text}</p>
              </div>
            ))}
            {pending ? <p className="assistant-thinking">Thinking carefully...</p> : null}
            {errorText ? <p className="form-error">{errorText}</p> : null}
          </div>

          <form className="assistant-form" onSubmit={handleSubmit}>
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about markets, stocks, news, or your portfolio"
              maxLength={700}
            />
            <button type="submit" className="button" disabled={pending || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      ) : null}

      <button type="button" className="assistant-fab" onClick={() => setIsOpen((prev) => !prev)}>
        <img src={botAvatar} alt="Open chatbot" className="assistant-fab-avatar" />
      </button>
    </div>
  )
}

export default AssistantChatbot
