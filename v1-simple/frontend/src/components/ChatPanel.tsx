/** 聊天面板组件 - 紧凑布局 */
import React, { useState, useRef, useEffect } from 'react';
import ReasoningChain from './ReasoningChain';
import type { StepEvent } from '../api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  element?: React.ReactNode;
}

interface Props {
  messages: Message[];
  onSend: (message: string) => void;
  loading: boolean;
  streamingSteps?: StepEvent[];
  pendingInput?: string;
  onPendingInputClear?: () => void;
}

const EXAMPLES = [
  "各险种赔付率排名",
  "理赔平均处理时效（按险种）",
  "客户年龄段保费分布",
  "各渠道佣金率对比",
  "产品续保率排名",
  "Top 10 代理人业绩排名",
  "2024年月度新单保费趋势",
  "寿险保费同比增长情况",
];

export default function ChatPanel({ messages, onSend, loading, streamingSteps = [], pendingInput, onPendingInputClear }: Props) {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // 当收到 pendingInput 时填入输入框并聚焦
  useEffect(() => {
    if (pendingInput) {
      setInput(pendingInput);
      onPendingInputClear?.();
      // 延迟聚焦，确保渲染完成
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [pendingInput, onPendingInputClear]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingSteps]);

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput('');
    onSend(msg);
  };

  return (
    <div style={styles.container}>
      <div style={styles.messages}>
        {messages.length === 0 && !loading && (
          <div style={styles.welcome}>
            <div style={{ fontSize: 28 }}>📊</div>
            <h2 style={{ margin: '4px 0', fontSize: 18 }}>AIA 智能数据分析</h2>
            <p style={{ color: '#6c7086', margin: '0 0 12px', fontSize: 13 }}>
              用自然语言提问，AI Agent 团队为你分析保险业务数据
            </p>
            <div style={styles.examples}>
              {EXAMPLES.map(ex => (
                <button key={ex} style={styles.exampleBtn} onClick={() => onSend(ex)} disabled={loading}>
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{ ...styles.messageRow, justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{ ...styles.messageContent, maxWidth: msg.role === 'user' ? '75%' : '100%' }}>
              <div style={{
                ...styles.bubble,
                backgroundColor: msg.role === 'user' ? '#89b4fa' : 'transparent',
                color: msg.role === 'user' ? '#11111b' : '#cdd6f4',
                borderRadius: msg.role === 'user' ? '14px 14px 4px 14px' : 0,
                padding: msg.role === 'user' ? '8px 12px' : '0',
              }}>
                {msg.content}
              </div>
              {msg.element && <div style={{ marginTop: 2 }}>{msg.element}</div>}
            </div>
          </div>
        ))}

        {loading && streamingSteps.length > 0 && (
          <div style={{ ...styles.messageRow, justifyContent: 'flex-start' }}>
            <div style={{ maxWidth: '100%' }}>
              <ReasoningChain steps={streamingSteps} isStreaming={true} />
            </div>
          </div>
        )}

        {loading && streamingSteps.length === 0 && (
          <div style={styles.loadingDot}>
            <span style={styles.dot}>●</span>
            <span style={{ ...styles.dot, animationDelay: '0.2s' }}>●</span>
            <span style={{ ...styles.dot, animationDelay: '0.4s' }}>●</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div style={styles.inputArea}>
        <div style={styles.inputWrapper}>
          <input
            ref={inputRef}
            style={styles.input}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="输入你的分析问题..."
            disabled={loading}
          />
          <button
            style={{ ...styles.sendBtn, opacity: loading || !input.trim() ? 0.4 : 1 }}
            onClick={handleSend}
            disabled={loading || !input.trim()}
          >↑</button>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    width: '100%',
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px 24px 8px',
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  welcome: {
    textAlign: 'center',
    color: '#cdd6f4',
    padding: '40px 0 24px',
  },
  examples: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
    justifyContent: 'center',
  },
  exampleBtn: {
    backgroundColor: '#1e1e2e',
    color: '#a6adc8',
    border: '1px solid #313244',
    borderRadius: 16,
    padding: '5px 12px',
    fontSize: 12,
    cursor: 'pointer',
  },
  messageRow: {
    display: 'flex',
    width: '100%',
  },
  messageContent: {
    display: 'flex',
    flexDirection: 'column',
  },
  bubble: {
    fontSize: 13,
    lineHeight: 1.6,
    wordBreak: 'break-word',
  },
  loadingDot: {
    display: 'flex',
    gap: 4,
    padding: '4px 0',
  },
  dot: {
    color: '#6c7086',
    fontSize: 8,
    animation: 'pulse 1s ease-in-out infinite',
  },
  inputArea: {
    padding: '4px 24px 12px',
  },
  inputWrapper: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#1e1e2e',
    border: '1px solid #313244',
    borderRadius: 20,
    padding: '2px 4px 2px 14px',
  },
  input: {
    flex: 1,
    backgroundColor: 'transparent',
    color: '#cdd6f4',
    border: 'none',
    padding: '8px 0',
    fontSize: 13,
    outline: 'none',
  },
  sendBtn: {
    backgroundColor: '#89b4fa',
    color: '#11111b',
    border: 'none',
    borderRadius: '50%',
    width: 30,
    height: 30,
    fontSize: 16,
    fontWeight: 700,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
};
