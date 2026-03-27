import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import botAvatar from '../assets/assistant-bot.svg'

function AssistantChatbot() {
  const bodyRef = useRef(null)
  const [isOpen, setIsOpen] = useState(false)
  const [input, setInput] = useState('')
  const [pending, setPending] = useState(false)
  const [feedbackMessage, setFeedbackMessage] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text:
        'Hello. I am here to help with stocks, market news, and your portfolio. Please ask anything related to finance in simple words.',
      interactionId: null,
      feedbackStatus: 'unrated',
      feedbackPending: false,
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

    try {
      const response = await api.post('/api/chatbot/', {
        question,
        history,
      })

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: response.data?.answer || 'I could not generate a response right now.',
          interactionId: response.data?.meta?.interaction_id || null,
          feedbackStatus: 'unrated',
          feedbackPending: false,
        },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: 'I am sorry, but I could not respond right now. Please try again in a moment.',
          interactionId: null,
          feedbackStatus: 'unrated',
          feedbackPending: false,
        },
      ])
    } finally {
      setPending(false)
    }
  }

  const sendFeedback = async (messageIndex, feedbackStatus) => {
    const target = messages[messageIndex]
    if (!target?.interactionId || target?.feedbackPending) return

    setFeedbackMessage('')
    setMessages((prev) =>
      prev.map((item, index) =>
        index === messageIndex
          ? {
              ...item,
              feedbackPending: true,
            }
          : item
      )
    )

    try {
      await api.post('/api/chatbot/feedback/', {
        interaction_id: target.interactionId,
        feedback_status: feedbackStatus,
      })
      setMessages((prev) =>
        prev.map((item, index) =>
          index === messageIndex
            ? {
                ...item,
                feedbackStatus,
                feedbackPending: false,
              }
            : item
        )
      )
      setFeedbackMessage(feedbackStatus === 'positive' ? 'Marked as useful.' : 'Marked as not useful.')
    } catch (error) {
      setMessages((prev) =>
        prev.map((item, index) =>
          index === messageIndex
            ? {
                ...item,
                feedbackPending: false,
              }
            : item
        )
      )
      const detail =
        error?.response?.data?.detail ||
        error?.response?.data?.feedback_status?.[0] ||
        'Could not save feedback right now.'
      setFeedbackMessage(detail)
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
                {msg.role === 'assistant' && msg.interactionId ? (
                  <div className="assistant-feedback">
                    <button
                      type="button"
                      className={`assistant-feedback-button ${msg.feedbackStatus === 'positive' ? 'assistant-feedback-active' : ''}`}
                      onClick={() => sendFeedback(index, 'positive')}
                      disabled={msg.feedbackPending}
                    >
                      {msg.feedbackPending && msg.feedbackStatus !== 'positive' ? 'Saving...' : 'Useful'}
                    </button>
                    <button
                      type="button"
                      className={`assistant-feedback-button ${msg.feedbackStatus === 'negative' ? 'assistant-feedback-active' : ''}`}
                      onClick={() => sendFeedback(index, 'negative')}
                      disabled={msg.feedbackPending}
                    >
                      {msg.feedbackPending && msg.feedbackStatus !== 'negative' ? 'Saving...' : 'Not useful'}
                    </button>
                  </div>
                ) : null}
              </div>
            ))}
            {pending ? <p className="assistant-thinking">Thinking carefully...</p> : null}
            {feedbackMessage ? <p className="assistant-feedback-message">{feedbackMessage}</p> : null}
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
