/** Agentic BI 助手 - 主应用（支持多轮对话 + Self-Correction + 反问澄清 + 建议点击） */
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useAppAuth } from './auth';
import ChatPanel from './components/ChatPanel';
import ReasoningChain from './components/ReasoningChain';
import ResultPanel from './components/ResultPanel';
import ConfigPage from './components/ConfigPage';
import { sendChat, type StepEvent, type ClarificationEvent } from './api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  element?: React.ReactNode;
}

export default function App() {
  const { signOut, getIdTokenClaims } = useAppAuth();
  const [userName, setUserName] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentSteps, setCurrentSteps] = useState<StepEvent[]>([]);
  const [page, setPage] = useState<'chat' | 'config'>('chat');
  const [pendingInput, setPendingInput] = useState('');
  const sessionIdRef = useRef<string | null>(null);

  useEffect(() => {
    getIdTokenClaims().then(claims => {
      if (claims) {
        const name = (claims as Record<string, unknown>)['name'] as string | undefined
          || (claims as Record<string, unknown>)['username'] as string | undefined
          || claims.sub;
        setUserName(name || '');
      }
    }).catch(() => {});
  }, [getIdTokenClaims]);

  const handleSend = useCallback(async (message: string) => {
    setPendingInput('');
    setLoading(true);
    setCurrentSteps([]);
    setMessages(prev => [...prev, { role: 'user', content: message }]);

    const steps: StepEvent[] = [];
    let resultReceived = false;

    await sendChat(
      message,
      sessionIdRef.current,
      // onStep
      (step) => { steps.push(step); setCurrentSteps([...steps]); },
      // onResult
      (result) => {
        resultReceived = true;
        if (result.session_id) sessionIdRef.current = result.session_id;

        const finalSteps = [...steps];
        const retryNote = (result.attempts && result.attempts > 1)
          ? `\n🔄 经过 ${result.attempts} 次尝试后得到结果`
          : '';
        const assistantMsg: Message = {
          role: 'assistant',
          content: (result.reviewer?.summary || '分析完成') + retryNote,
          element: (
            <div>
              <ReasoningChain steps={finalSteps} isStreaming={false} />
              <ResultPanel
                data={result.executor.data}
                columns={result.executor.columns}
                chartType={result.executor.chart_suggestion}
                summary={result.reviewer?.summary}
                suggestions={result.reviewer?.suggestions}
                onSuggestionClick={(text) => setPendingInput(text)}
              />
            </div>
          ),
        };
        setMessages(prev => [...prev, assistantMsg]);
        setLoading(false);
        setCurrentSteps([]);
      },
      // onError
      (error) => {
        resultReceived = true;
        setMessages(prev => [...prev, { role: 'assistant', content: `❌ 出错了: ${error}` }]);
        setLoading(false);
        setCurrentSteps([]);
      },
      // onSession
      (sid) => { sessionIdRef.current = sid; },
      // onClarification
      (clarification: ClarificationEvent) => {
        resultReceived = true;
        if (clarification.session_id) sessionIdRef.current = clarification.session_id;

        const finalSteps = [...steps];
        const assistantMsg: Message = {
          role: 'assistant',
          content: clarification.question,
          element: (
            <div>
              <ReasoningChain steps={finalSteps} isStreaming={false} />
              <div style={clarStyles.container}>
                <div style={clarStyles.question}>❓ {clarification.question}</div>
                {clarification.options && clarification.options.length > 0 && (
                  <div style={clarStyles.options}>
                    {clarification.options.map((opt, i) => (
                      <button
                        key={i}
                        style={clarStyles.optionBtn}
                        onClick={() => setPendingInput(opt)}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
                {clarification.missing_params && clarification.missing_params.length > 0 && (
                  <div style={clarStyles.missing}>
                    缺少参数: {clarification.missing_params.join(', ')}
                  </div>
                )}
              </div>
            </div>
          ),
        };
        setMessages(prev => [...prev, assistantMsg]);
        setLoading(false);
        setCurrentSteps([]);
      },
    );

    if (!resultReceived) {
      setMessages(prev => [...prev, { role: 'assistant', content: '⚠️ 分析流程已结束，但未收到完整结果。请重试。' }]);
      setLoading(false);
      setCurrentSteps([]);
    }
  }, []);

  const handleNewChat = () => {
    sessionIdRef.current = null;
    setMessages([]);
    setCurrentSteps([]);
    setPendingInput('');
  };

  if (page === 'config') {
    return <ConfigPage onBack={() => setPage('chat')} />;
  }

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.title}>📊 AIA Agentic BI</h1>
        <span style={styles.subtitle}>Router → Executor → Reviewer</span>
        <div style={styles.headerRight}>
          {messages.length > 0 && (
            <button onClick={handleNewChat} style={styles.newChatBtn}>+ 新对话</button>
          )}
          <button onClick={() => setPage('config')} style={styles.configBtn}>⚙️ 系统配置</button>
          {userName && <span style={styles.userName}>👤 {userName}</span>}
          <button onClick={() => void signOut(window.location.origin)} style={styles.logoutBtn}>退出</button>
        </div>
      </header>
      <main style={styles.main}>
        <ChatPanel
          messages={messages}
          onSend={handleSend}
          loading={loading}
          streamingSteps={currentSteps}
          pendingInput={pendingInput}
          onPendingInputClear={() => setPendingInput('')}
        />
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    height: '100vh',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#11111b',
    color: '#cdd6f4',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '8px 20px',
    backgroundColor: '#181825',
    borderBottom: '1px solid #313244',
  },
  title: { margin: 0, fontSize: 18 },
  subtitle: { color: '#6c7086', fontSize: 12 },
  headerRight: { marginLeft: 'auto', display: 'flex', gap: 8 },
  newChatBtn: {
    background: 'none',
    border: '1px solid #89b4fa',
    color: '#89b4fa',
    borderRadius: 6,
    padding: '4px 12px',
    fontSize: 12,
    cursor: 'pointer',
  },
  configBtn: {
    background: 'none',
    border: '1px solid #313244',
    color: '#a6adc8',
    borderRadius: 6,
    padding: '4px 12px',
    fontSize: 12,
    cursor: 'pointer',
  },
  userName: {
    fontSize: 12,
    color: '#a6e3a1',
  },
  logoutBtn: {
    background: 'none',
    border: '1px solid #f38ba8',
    color: '#f38ba8',
    borderRadius: 6,
    padding: '4px 12px',
    fontSize: 12,
    cursor: 'pointer',
  },
  main: {
    flex: 1,
    display: 'flex',
    overflow: 'hidden',
  },
};

const clarStyles: Record<string, React.CSSProperties> = {
  container: {
    marginTop: 6,
    padding: '8px 12px',
    backgroundColor: '#1e1e2e',
    borderRadius: 8,
    border: '1px solid #313244',
  },
  question: {
    fontSize: 14,
    color: '#cdd6f4',
    marginBottom: 8,
    lineHeight: 1.5,
  },
  options: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 4,
  },
  optionBtn: {
    backgroundColor: '#181825',
    color: '#89b4fa',
    border: '1px solid #89b4fa44',
    borderRadius: 16,
    padding: '4px 14px',
    fontSize: 13,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  missing: {
    fontSize: 11,
    color: '#585b70',
    marginTop: 4,
  },
};
