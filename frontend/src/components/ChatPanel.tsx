import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Send, Bot, User, Sparkles, RotateCcw } from 'lucide-react'
import { useStore } from '../store'
import { chatApi } from '../api'
import toast from 'react-hot-toast'
import type { Message } from '../types'

const SUGGESTIONS = [
  '我想去日本东京玩5天，预算1万元',
  '帮我规划一个泰国清迈3天行程',
  '推荐一些适合情侣的巴厘岛酒店',
  '五一假期去云南大理，预算5000元',
]

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      {[0, 1, 2].map((i) => (
        <span key={i} className="w-2 h-2 rounded-full bg-blue-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }} />
      ))}
    </div>
  )
}

function ChatBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${isUser ? 'gradient-bg' : 'bg-blue-50 border border-blue-100'}`}>
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-blue-500" />}
      </div>
      <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
        isUser ? 'gradient-bg text-white rounded-tr-sm' : 'bg-white border border-gray-100 shadow-sm text-gray-800 rounded-tl-sm'
      }`}>
        {isUser ? (
          <p>{msg.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ChatPanel() {
  const { messages, isLoading, threadId, addMessage, setLoading, setThreadId, clearChat } = useStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const send = async (text?: string) => {
    const content = (text ?? input).trim()
    if (!content || isLoading) return
    setInput('')

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content, timestamp: new Date() }
    addMessage(userMsg)
    setLoading(true)

    try {
      const res = await chatApi.send(content, threadId ?? undefined)
      const { reply, thread_id } = res.data
      setThreadId(thread_id)
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: reply,
        timestamp: new Date(),
        trip_plan: res.data.trip_plan as Message['trip_plan'],
      }
      addMessage(aiMsg)
    } catch {
      toast.error('Failed to get response. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-blue-500" />
          <h2 className="font-semibold text-gray-900">AI Travel Concierge</h2>
          <span className="text-xs bg-green-100 text-green-600 px-2 py-0.5 rounded-full font-medium">Online</span>
        </div>
        <button onClick={clearChat} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors" title="New conversation">
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto scrollbar-hide p-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-16 h-16 rounded-2xl gradient-bg flex items-center justify-center mb-4 shadow-lg">
              <Bot className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">How can I help you travel?</h3>
            <p className="text-gray-500 text-sm mb-8 max-w-sm">Tell me your destination, dates, and budget — I'll plan everything for you.</p>
            <div className="grid grid-cols-1 gap-2 w-full max-w-sm">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="text-left px-4 py-3 rounded-xl bg-white border border-gray-200 hover:border-blue-300 hover:bg-blue-50 text-sm text-gray-700 transition-all shadow-sm">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => <ChatBubble key={msg.id} msg={msg} />)}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-50 border border-blue-100 flex items-center justify-center">
              <Bot className="w-4 h-4 text-blue-500" />
            </div>
            <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-tl-sm">
              <TypingDots />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-100 bg-white">
        <div className="flex gap-3 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder="Tell me where you want to go..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent max-h-32 overflow-y-auto"
            style={{ minHeight: '48px' }}
          />
          <button onClick={() => send()} disabled={!input.trim() || isLoading}
            className="w-12 h-12 rounded-xl gradient-bg flex items-center justify-center text-white hover:opacity-90 transition-opacity disabled:opacity-40 flex-shrink-0 shadow-md">
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">Press Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  )
}
