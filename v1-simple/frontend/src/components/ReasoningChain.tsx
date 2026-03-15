/** 推理链展示组件 - 每步骤展示详细结果，默认折叠 */
import React, { useState, useEffect } from 'react';
import type { StepEvent } from '../api';

interface Props {
  steps: StepEvent[];
  isStreaming?: boolean;
}

const agentLabel: Record<string, string> = {
  router: 'Router',
  executor: 'Executor',
  reviewer: 'Reviewer',
};

const agentColor: Record<string, string> = {
  router: '#cba6f7',   // purple
  executor: '#89b4fa',  // blue
  reviewer: '#a6e3a1',  // green
};

function deduplicateSteps(steps: StepEvent[]): StepEvent[] {
  const result: StepEvent[] = [];
  for (let i = 0; i < steps.length; i++) {
    const agent = steps[i].agent;
    const hasDone = steps.some((s, j) => j > i && s.agent === agent && s.status === 'done');
    if (steps[i].status === 'running' && hasDone) continue;
    result.push(steps[i]);
  }
  return result;
}

function stripEmoji(msg: string): string {
  return msg.replace(/^[\u{1F300}-\u{1FFFF}\u{2600}-\u{27BF}\u{FE00}-\u{FEFF}✅❌⏳🧭⚙️🔍🔄⚠️]+\s*/u, '');
}

/** CSS spinner via inline style + keyframes injection */
const SPINNER_ID = 'rc-spinner-style';
function ensureSpinnerCSS() {
  if (typeof document === 'undefined') return;
  if (document.getElementById(SPINNER_ID)) return;
  const style = document.createElement('style');
  style.id = SPINNER_ID;
  style.textContent = `
    @keyframes rc-spin { to { transform: rotate(360deg); } }
    .rc-spinner {
      display: inline-block;
      width: 12px; height: 12px;
      border: 1.5px solid #45475a;
      border-top-color: #89b4fa;
      border-radius: 50%;
      animation: rc-spin 0.8s linear infinite;
      flex-shrink: 0;
      margin-right: 4px;
      vertical-align: middle;
    }
  `;
  document.head.appendChild(style);
}

/** 渲染 Router 步骤详情 */
function RouterDetail({ detail }: { detail: any }) {
  if (!detail) return null;
  return (
    <div style={detailStyles.box}>
      {detail.skill_name && (
        <div style={detailStyles.row}>
          <span style={detailStyles.key}>技能</span>
          <span style={{ ...detailStyles.val, color: '#89b4fa' }}>{detail.skill_name}</span>
        </div>
      )}
      {detail.parameters && Object.keys(detail.parameters).length > 0 && (
        <div style={detailStyles.row}>
          <span style={detailStyles.key}>参数</span>
          <span style={detailStyles.val}>
            {Object.entries(detail.parameters).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join('  ')}
          </span>
        </div>
      )}
      {detail.reasoning && (
        <div style={detailStyles.row}>
          <span style={detailStyles.key}>推理</span>
          <span style={detailStyles.val}>{detail.reasoning}</span>
        </div>
      )}
    </div>
  );
}

/** 渲染 Executor 步骤详情 */
function ExecutorDetail({ detail }: { detail: any }) {
  if (!detail) return null;
  return (
    <div style={detailStyles.box}>
      {detail.sql && (
        <div style={detailStyles.sqlBlock}>
          <pre style={detailStyles.sql}>{detail.sql}</pre>
        </div>
      )}
      <div style={detailStyles.row}>
        {detail.success !== undefined && (
          <>
            <span style={detailStyles.key}>状态</span>
            <span style={{ ...detailStyles.val, color: detail.success ? '#a6e3a1' : '#f38ba8' }}>
              {detail.success ? '成功' : '失败'}
            </span>
          </>
        )}
        {detail.row_count !== undefined && (
          <>
            <span style={{ ...detailStyles.key, marginLeft: 12 }}>行数</span>
            <span style={detailStyles.val}>{detail.row_count}</span>
          </>
        )}
        {detail.chart_suggestion && (
          <>
            <span style={{ ...detailStyles.key, marginLeft: 12 }}>图表</span>
            <span style={detailStyles.val}>{detail.chart_suggestion}</span>
          </>
        )}
      </div>
      {detail.error && (
        <div style={detailStyles.row}>
          <span style={detailStyles.key}>错误</span>
          <span style={{ ...detailStyles.val, color: '#f38ba8' }}>{detail.error}</span>
        </div>
      )}
    </div>
  );
}

/** 渲染 Reviewer 步骤详情 */
function ReviewerDetail({ detail }: { detail: any }) {
  if (!detail) return null;
  return (
    <div style={detailStyles.box}>
      {detail.is_valid !== undefined && (
        <div style={detailStyles.row}>
          <span style={detailStyles.key}>结果</span>
          <span style={{ ...detailStyles.val, color: detail.is_valid ? '#a6e3a1' : '#fab387' }}>
            {detail.is_valid ? '✅ 通过' : '⚠️ 未通过'}
          </span>
        </div>
      )}
      {detail.summary && (
        <div style={detailStyles.row}>
          <span style={detailStyles.key}>评价</span>
          <span style={detailStyles.val}>{detail.summary}</span>
        </div>
      )}
      {detail.correction_hint && !detail.is_valid && (
        <div style={detailStyles.row}>
          <span style={detailStyles.key}>修正</span>
          <span style={{ ...detailStyles.val, color: '#fab387' }}>{detail.correction_hint}</span>
        </div>
      )}
    </div>
  );
}

const DetailComponent: Record<string, React.FC<{ detail: any }>> = {
  router: RouterDetail,
  executor: ExecutorDetail,
  reviewer: ReviewerDetail,
};

export default function ReasoningChain({ steps, isStreaming = false }: Props) {
  // 默认折叠，流式时展开
  const [expanded, setExpanded] = useState(false);

  useEffect(() => { ensureSpinnerCSS(); }, []);

  useEffect(() => {
    if (isStreaming) setExpanded(true);
    // 流式结束后保持当前状态（不自动折叠）
  }, [isStreaming]);

  if (steps.length === 0) return null;

  const display = deduplicateSteps(steps);
  const doneCount = display.filter(s => s.status === 'done').length;
  const lastRunning = display.find(s => s.status === 'running');

  return (
    <div style={styles.container}>
      <button onClick={() => setExpanded(!expanded)} style={styles.toggle}>
        {isStreaming ? (
          <span className="rc-spinner" />
        ) : (
          <span style={styles.caret}>{expanded ? '▾' : '▸'}</span>
        )}
        <span style={styles.label}>
          {isStreaming
            ? (lastRunning ? stripEmoji(lastRunning.message) : '思考中...')
            : `已完成 · ${doneCount} 个步骤`}
        </span>
      </button>

      {expanded && (
        <div style={styles.list}>
          {display.map((step, i) => {
            const isRunning = step.status === 'running';
            const Detail = DetailComponent[step.agent];
            return (
              <div key={i} style={styles.stepBlock}>
                <div style={styles.item}>
                  {isRunning && <span className="rc-spinner" />}
                  {!isRunning && <span style={styles.checkmark}>✓</span>}
                  <span style={{
                    ...styles.agentTag,
                    color: agentColor[step.agent] || '#585b70',
                    borderColor: (agentColor[step.agent] || '#313244') + '44',
                  }}>
                    {agentLabel[step.agent] || step.agent}
                  </span>
                  <span style={{ ...styles.text, color: isRunning ? '#a6adc8' : '#7f849c' }}>
                    {stripEmoji(step.message)}
                  </span>
                </div>
                {!isRunning && step.detail && Detail && (
                  <Detail detail={step.detail} />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { margin: '2px 0 4px 0' },
  toggle: {
    background: 'none',
    border: 'none',
    color: '#585b70',
    fontSize: 12,
    cursor: 'pointer',
    padding: '2px 0',
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    fontFamily: 'inherit',
  },
  caret: { fontSize: 10, width: 12, color: '#45475a', textAlign: 'center' as const },
  label: { fontStyle: 'italic' },
  list: {
    marginTop: 2,
    paddingLeft: 12,
    borderLeft: '1.5px solid #313244',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 2,
  },
  stepBlock: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 0,
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap' as const,
    lineHeight: '20px',
  },
  checkmark: {
    fontSize: 10,
    color: '#a6e3a1',
    width: 12,
    textAlign: 'center' as const,
    flexShrink: 0,
  },
  agentTag: {
    fontSize: 10,
    backgroundColor: '#1e1e2e',
    padding: '1px 6px',
    borderRadius: 3,
    flexShrink: 0,
    fontFamily: 'monospace',
    border: '1px solid #313244',
  },
  text: { fontSize: 12, flexShrink: 1, wordBreak: 'break-word' as const },
};

const detailStyles: Record<string, React.CSSProperties> = {
  box: {
    marginLeft: 28,
    marginTop: 2,
    marginBottom: 4,
    padding: '4px 8px',
    backgroundColor: '#181825',
    borderRadius: 4,
    border: '1px solid #1e1e2e',
    fontSize: 11,
  },
  row: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 6,
    lineHeight: '18px',
    flexWrap: 'wrap' as const,
  },
  key: {
    color: '#45475a',
    fontSize: 10,
    flexShrink: 0,
    minWidth: 28,
  },
  val: {
    color: '#7f849c',
    wordBreak: 'break-word' as const,
  },
  sqlBlock: {
    marginBottom: 4,
  },
  sql: {
    backgroundColor: '#11111b',
    color: '#a6e3a1',
    padding: 6,
    borderRadius: 4,
    fontSize: 10,
    margin: 0,
    overflowX: 'auto' as const,
    whiteSpace: 'pre-wrap' as const,
    lineHeight: 1.3,
  },
};
