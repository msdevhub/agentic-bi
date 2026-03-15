/** 系统配置页面 - Agent/Skill/Data 全貌 + 模型配置 */
import React, { useEffect, useState } from 'react';

interface Agent {
  name: string;
  role: string;
  description: string;
  model: string;
  system_prompt: string;
}

interface Skill {
  name: string;
  description: string;
  parameters: Record<string, any>;
}

interface TableInfo {
  table: string;
  columns: { name: string; type: string }[];
  row_count: number;
  sample_data: Record<string, any>[];
}

interface SystemConfig {
  agents: Agent[];
  skills: Skill[];
  tables: TableInfo[];
  architecture: {
    flow: string;
    features?: string[];
    tech_stack: Record<string, string>;
  };
}

interface ModelConfig {
  agents: Record<string, { model: string; description?: string }>;
  available_models: string[];
}

// Agent name → config key mapping
const AGENT_CONFIG_KEY: Record<string, string> = {
  'Router Agent': 'router',
  'Reviewer Agent': 'reviewer',
};

export default function ConfigPage({ onBack }: { onBack: () => void }) {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [modelConfig, setModelConfig] = useState<ModelConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedPrompt, setExpandedPrompt] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  useEffect(() => {
    Promise.all([
      fetch('/api/system-config').then(r => r.json()),
      fetch('/api/config').then(r => r.json()),
    ]).then(([sysData, cfgData]) => {
      setConfig(sysData);
      setModelConfig(cfgData);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleModelChange = async (agentKey: string, model: string) => {
    if (!modelConfig) return;
    const updated = {
      ...modelConfig,
      agents: {
        ...modelConfig.agents,
        [agentKey]: { ...modelConfig.agents[agentKey], model },
      },
    };
    setModelConfig(updated);

    // 同时更新 config 里的 agent model 显示
    if (config) {
      const agentName = Object.entries(AGENT_CONFIG_KEY).find(([, v]) => v === agentKey)?.[0];
      if (agentName) {
        setConfig({
          ...config,
          agents: config.agents.map(a => a.name === agentName ? { ...a, model } : a),
        });
      }
    }

    // 保存到后端
    setSaving(true);
    setSaveMsg('');
    try {
      const res = await fetch('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agents: { [agentKey]: { model } } }),
      });
      if (res.ok) {
        setSaveMsg('✅ 已保存');
      } else {
        setSaveMsg('❌ 保存失败');
      }
    } catch {
      setSaveMsg('❌ 网络错误');
    }
    setSaving(false);
    setTimeout(() => setSaveMsg(''), 2000);
  };

  if (loading) return <div style={styles.loading}>加载中...</div>;
  if (!config) return <div style={styles.loading}>加载失败</div>;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button onClick={onBack} style={styles.backBtn}>← 返回聊天</button>
        <h2 style={styles.title}>⚙️ 系统配置</h2>
        {saveMsg && <span style={styles.saveMsg}>{saveMsg}</span>}
      </div>

      <div style={styles.content}>
        {/* 架构概览 */}
        <section style={styles.section}>
          <h3 style={styles.sectionTitle}>🏗️ 架构概览</h3>
          <div style={styles.flowBox}>
            <div style={styles.flow}>{config.architecture.flow}</div>
          </div>
          <div style={styles.tags}>
            {Object.entries(config.architecture.tech_stack).map(([k, v]) => (
              <span key={k} style={styles.tag}>
                <span style={styles.tagLabel}>{k}</span> {v}
              </span>
            ))}
          </div>
        </section>

        {/* Agent 列表 + 模型选择 */}
        <section style={styles.section}>
          <h3 style={styles.sectionTitle}>🤖 Agent 配置</h3>
          <div style={styles.cards}>
            {config.agents.map(agent => {
              const cfgKey = AGENT_CONFIG_KEY[agent.name];
              const canChangeModel = !!cfgKey && !!modelConfig;
              return (
                <div key={agent.name} style={styles.card}>
                  <div style={styles.cardHeader}>
                    <span style={styles.cardTitle}>{agent.name}</span>
                    {canChangeModel ? (
                      <select
                        value={modelConfig!.agents[cfgKey]?.model || agent.model}
                        onChange={e => handleModelChange(cfgKey, e.target.value)}
                        style={styles.modelSelect}
                        disabled={saving}
                      >
                        {modelConfig!.available_models.map(m => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                    ) : (
                      <span style={styles.badge}>{agent.model}</span>
                    )}
                  </div>
                  <div style={styles.cardRole}>{agent.role}</div>
                  <div style={styles.cardDesc}>{agent.description}</div>
                  <button
                    style={styles.promptToggle}
                    onClick={() => setExpandedPrompt(expandedPrompt === agent.name ? null : agent.name)}
                  >
                    {expandedPrompt === agent.name ? '▾' : '▸'} System Prompt
                  </button>
                  {expandedPrompt === agent.name && (
                    <pre style={styles.prompt}>{agent.system_prompt}</pre>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* 技能列表 */}
        <section style={styles.section}>
          <h3 style={styles.sectionTitle}>🔧 技能库 ({config.skills.length} Skills)</h3>
          <div style={styles.cards}>
            {config.skills.map(skill => (
              <div key={skill.name} style={styles.card}>
                <div style={styles.cardHeader}>
                  <span style={styles.cardTitle}>{skill.name}</span>
                </div>
                <div style={styles.cardDesc}>{skill.description}</div>
                <div style={styles.paramList}>
                  {Object.entries(skill.parameters).map(([k, v]: [string, any]) => (
                    <div key={k} style={styles.param}>
                      <code style={styles.paramName}>{k}</code>
                      <span style={styles.paramType}>{v.type}{v.enum ? ` [${v.enum.join('|')}]` : ''}</span>
                      <span style={styles.paramDesc}>{v.description}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 数据概览 */}
        <section style={styles.section}>
          <h3 style={styles.sectionTitle}>📊 数据表 ({config.tables.length} Tables)</h3>
          {config.tables.map(t => (
            <div key={t.table} style={{ ...styles.card, marginBottom: 8 }}>
              <div style={styles.cardHeader}>
                <span style={styles.cardTitle}>{t.table}</span>
                <span style={styles.badge}>{t.row_count.toLocaleString()} 行</span>
              </div>
              <div style={styles.colList}>
                {t.columns.map(c => (
                  <span key={c.name} style={styles.colTag}>
                    {c.name} <span style={styles.colType}>{c.type}</span>
                  </span>
                ))}
              </div>
              {t.sample_data.length > 0 && (
                <div style={styles.tableWrapper}>
                  <table style={styles.table}>
                    <thead>
                      <tr>{t.columns.map(c => <th key={c.name} style={styles.th}>{c.name}</th>)}</tr>
                    </thead>
                    <tbody>
                      {t.sample_data.map((row, i) => (
                        <tr key={i}>
                          {t.columns.map(c => (
                            <td key={c.name} style={styles.td}>
                              {typeof row[c.name] === 'number'
                                ? row[c.name].toLocaleString('zh-CN', { maximumFractionDigits: 2 })
                                : String(row[c.name] ?? '')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#11111b',
    color: '#cdd6f4',
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#6c7086',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 20px',
    borderBottom: '1px solid #313244',
    backgroundColor: '#181825',
  },
  backBtn: {
    background: 'none',
    border: '1px solid #313244',
    color: '#89b4fa',
    borderRadius: 6,
    padding: '4px 12px',
    fontSize: 12,
    cursor: 'pointer',
  },
  title: { margin: 0, fontSize: 16 },
  saveMsg: {
    fontSize: 12,
    color: '#a6e3a1',
    marginLeft: 'auto',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
  },
  section: {},
  sectionTitle: {
    margin: '0 0 8px 0',
    fontSize: 14,
    color: '#89b4fa',
  },
  flowBox: {
    backgroundColor: '#181825',
    borderRadius: 6,
    padding: '10px 14px',
    marginBottom: 8,
  },
  flow: {
    fontSize: 13,
    color: '#a6adc8',
    lineHeight: 1.6,
  },
  tags: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
  },
  tag: {
    backgroundColor: '#1e1e2e',
    border: '1px solid #313244',
    borderRadius: 4,
    padding: '3px 8px',
    fontSize: 11,
    color: '#a6adc8',
  },
  tagLabel: {
    color: '#89b4fa',
    fontWeight: 600,
    marginRight: 4,
  },
  cards: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  card: {
    backgroundColor: '#181825',
    border: '1px solid #313244',
    borderRadius: 6,
    padding: '10px 14px',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  cardTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: '#cdd6f4',
  },
  badge: {
    fontSize: 10,
    color: '#a6e3a1',
    backgroundColor: '#1e1e2e',
    padding: '1px 8px',
    borderRadius: 10,
    border: '1px solid #313244',
  },
  modelSelect: {
    fontSize: 12,
    color: '#cdd6f4',
    backgroundColor: '#1e1e2e',
    border: '1px solid #313244',
    borderRadius: 6,
    padding: '3px 8px',
    cursor: 'pointer',
    outline: 'none',
  },
  cardRole: {
    fontSize: 11,
    color: '#89b4fa',
    marginBottom: 2,
  },
  cardDesc: {
    fontSize: 12,
    color: '#6c7086',
    lineHeight: 1.5,
  },
  promptToggle: {
    background: 'none',
    border: 'none',
    color: '#585b70',
    fontSize: 11,
    cursor: 'pointer',
    padding: '4px 0 0',
    fontFamily: 'inherit',
  },
  prompt: {
    backgroundColor: '#11111b',
    color: '#a6adc8',
    padding: 8,
    borderRadius: 4,
    fontSize: 11,
    marginTop: 4,
    whiteSpace: 'pre-wrap',
    lineHeight: 1.5,
    maxHeight: 300,
    overflowY: 'auto',
  },
  paramList: {
    marginTop: 6,
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
  },
  param: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 6,
    fontSize: 11,
  },
  paramName: {
    color: '#f9e2af',
    backgroundColor: '#11111b',
    padding: '0 4px',
    borderRadius: 2,
    fontFamily: 'monospace',
    flexShrink: 0,
  },
  paramType: {
    color: '#585b70',
    fontSize: 10,
    flexShrink: 0,
  },
  paramDesc: {
    color: '#6c7086',
  },
  colList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
    marginTop: 6,
    marginBottom: 6,
  },
  colTag: {
    backgroundColor: '#11111b',
    padding: '1px 6px',
    borderRadius: 3,
    fontSize: 11,
    color: '#cdd6f4',
  },
  colType: {
    color: '#585b70',
    fontSize: 10,
    marginLeft: 2,
  },
  tableWrapper: {
    overflowX: 'auto',
    borderRadius: 4,
    border: '1px solid #313244',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 10,
  },
  th: {
    backgroundColor: '#1e1e2e',
    color: '#89b4fa',
    padding: '3px 6px',
    textAlign: 'left',
    borderBottom: '1px solid #313244',
    whiteSpace: 'nowrap',
  },
  td: {
    padding: '2px 6px',
    color: '#bac2de',
    borderBottom: '1px solid #1e1e2e',
    whiteSpace: 'nowrap',
  },
};
