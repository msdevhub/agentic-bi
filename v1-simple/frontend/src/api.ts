/** API 层 - 与后端通信（支持 session_id 多轮对话 + 反问澄清） */

export interface StepEvent {
  agent: string;
  status: 'running' | 'done';
  message: string;
  detail?: any;
}

export interface ClarificationEvent {
  question: string;
  options: string[];
  missing_params: string[];
  session_id?: string;
}

export interface ChatResult {
  session_id?: string;
  attempts?: number;
  router: {
    skill_name: string;
    parameters: Record<string, any>;
    reasoning: string;
  };
  executor: {
    sql: string;
    data: Record<string, any>[];
    columns: string[];
    row_count: number;
    chart_suggestion: string;
    success: boolean;
  };
  reviewer: {
    summary: string;
    is_valid: boolean;
    suggestions: string[];
  };
}

export async function sendChat(
  message: string,
  sessionId: string | null,
  onStep: (step: StepEvent) => void,
  onResult: (result: ChatResult) => void,
  onError: (error: string) => void,
  onSession?: (sessionId: string) => void,
  onClarification?: (c: ClarificationEvent) => void,
) {
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    if (!res.ok) { onError(`HTTP ${res.status}`); return; }
    const reader = res.body?.getReader();
    if (!reader) { onError('No response body'); return; }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const norm = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
      const blocks = norm.split('\n\n');
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        processBlock(block, onStep, onResult, onSession, onClarification);
      }
    }

    if (buffer.trim()) {
      processBlock(buffer, onStep, onResult, onSession, onClarification);
    }
  } catch (e: any) {
    onError(e.message || 'Unknown error');
  }
}

function processBlock(
  block: string,
  onStep: (s: StepEvent) => void,
  onResult: (r: ChatResult) => void,
  onSession?: (id: string) => void,
  onClarification?: (c: ClarificationEvent) => void,
) {
  if (!block.trim()) return;
  let eventType = '';
  const dataLines: string[] = [];
  for (const line of block.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n')) {
    const t = line.trim();
    if (t.startsWith('event:')) eventType = t.slice(6).trim();
    else if (t.startsWith('data:')) dataLines.push(t.slice(5).trim());
  }
  if (!dataLines.length) return;
  try {
    const parsed = JSON.parse(dataLines.join('\n'));
    if (eventType === 'step') onStep(parsed);
    else if (eventType === 'result') onResult(parsed);
    else if (eventType === 'clarification' && onClarification) onClarification(parsed);
    else if (eventType === 'session' && parsed.session_id && onSession) onSession(parsed.session_id);
  } catch { /* ignore */ }
}
