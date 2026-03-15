/** 结果展示组件 - 图表 + 表格 + 建议 */
import React, { useMemo } from 'react';
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

interface Props {
  data: Record<string, any>[];
  columns: string[];
  chartType: string;
  summary?: string;
  suggestions?: string[];
  onSuggestionClick?: (text: string) => void;
}

/** 智能选择 X 轴（第一个非数值列）和 Y 轴（第一个数值列） */
function pickAxes(data: Record<string, any>[], columns: string[]) {
  let xCol = columns[0];
  let yCol = '';
  const yCols: string[] = [];

  for (const col of columns) {
    const sample = data.find(r => r[col] != null)?.[col];
    if (typeof sample === 'number') {
      if (!yCol) yCol = col;
      yCols.push(col);
    }
  }
  for (const col of columns) {
    const sample = data.find(r => r[col] != null)?.[col];
    if (typeof sample !== 'number') { xCol = col; break; }
  }
  return { xCol, yCol: yCol || columns[1], yCols };
}

function fmtTick(v: any): string {
  // 年份数值原样显示
  if (typeof v === 'number' && isYear(v)) return String(v);
  const s = String(v);
  // 年份字符串也原样显示
  if (/^\d{4}$/.test(s) && +s >= 1900 && +s <= 2100) return s;
  const m = s.match(/(\d{4})-(\d{2})(?:-(\d{2}))?/);
  if (m) return m[1].slice(2) + '-' + m[2];
  return s.length > 8 ? s.slice(0, 8) + '..' : s;
}

/** 判断一个数值是否像年份（1900-2100 的整数） */
function isYear(v: number): boolean {
  return Number.isInteger(v) && v >= 1900 && v <= 2100;
}

function fmtVal(v: any): string {
  if (typeof v === 'number') {
    // 年份原样显示，不做缩写
    if (isYear(v)) return String(v);
    if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(1) + 'M';
    if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(1) + 'K';
    return v.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  }
  return String(v ?? '').replace(/T00:00:00$/, '');
}

const TT_STYLE = { backgroundColor: '#1e1e2e', border: '1px solid #313244', borderRadius: 6, fontSize: 11, padding: '6px 8px' };
const TT_LABEL = (l: any) => String(l).replace(/T[\d:]+$/, '');
const TT_FMT = (v: any) => fmtVal(v);

export default function ResultPanel({ data, columns, chartType, suggestions, onSuggestionClick }: Props) {
  const { xCol, yCol } = useMemo(() => pickAxes(data, columns), [data, columns]);

  if (data.length === 0) return null;

  const showChart = chartType !== 'table' && data.length > 1 && !!yCol;
  // 无图表时默认展开表格
  const [showTable, setShowTable] = React.useState(!showChart);

  return (
    <div style={styles.container}>
      {showChart && (
        <div style={styles.chart}>
          <ResponsiveContainer width="100%" height={200}>
            {chartType === 'line' ? (
              <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#313244" />
                <XAxis dataKey={xCol} stroke="#6c7086" fontSize={10} tickFormatter={fmtTick} interval="preserveStartEnd" />
                <YAxis stroke="#6c7086" fontSize={10} tickFormatter={fmtVal} />
                <Tooltip contentStyle={TT_STYLE} labelStyle={{ color: '#cdd6f4' }} formatter={TT_FMT} labelFormatter={TT_LABEL} />
                <Line type="monotone" dataKey={yCol} stroke="#89b4fa" strokeWidth={2} dot={{ r: 2 }} />
              </LineChart>
            ) : (
              <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#313244" />
                <XAxis dataKey={xCol} stroke="#6c7086" fontSize={10} tickFormatter={fmtTick} interval={0} />
                <YAxis stroke="#6c7086" fontSize={10} tickFormatter={fmtVal} />
                <Tooltip contentStyle={TT_STYLE} labelStyle={{ color: '#cdd6f4' }} formatter={TT_FMT} labelFormatter={TT_LABEL} />
                <Bar dataKey={yCol} fill="#89b4fa" radius={[3, 3, 0, 0]} />
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      )}

      <button onClick={() => setShowTable(!showTable)} style={styles.tableToggle}>
        {showTable ? '▾' : '▸'} 数据表格 ({data.length} 行)
      </button>

      {showTable && (
        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>{columns.map(col => <th key={col} style={styles.th}>{col}</th>)}</tr>
            </thead>
            <tbody>
              {data.slice(0, 50).map((row, i) => (
                <tr key={i} style={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                  {columns.map(col => <td key={col} style={styles.td}>{fmtVal(row[col])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {suggestions && suggestions.length > 0 && (
        <div style={styles.suggestions}>
          <span style={styles.sugLabel}>💡</span>
          {suggestions.map((s, i) => (
            <span
              key={i}
              style={styles.sugItem}
              onClick={() => onSuggestionClick?.(s)}
              role="button"
              tabIndex={0}
            >
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { marginTop: 4 },
  chart: {
    backgroundColor: '#181825',
    padding: '8px 4px 0',
    borderRadius: 6,
    marginBottom: 2,
  },
  tableToggle: {
    background: 'none',
    border: 'none',
    color: '#585b70',
    fontSize: 11,
    cursor: 'pointer',
    padding: '2px 0',
    fontFamily: 'inherit',
  },
  tableWrapper: {
    overflowX: 'auto',
    borderRadius: 6,
    border: '1px solid #313244',
    marginBottom: 4,
  },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 11 },
  th: {
    backgroundColor: '#181825',
    color: '#89b4fa',
    padding: '4px 8px',
    textAlign: 'left',
    borderBottom: '1px solid #313244',
    whiteSpace: 'nowrap',
    fontWeight: 500,
  },
  td: {
    padding: '3px 8px',
    color: '#bac2de',
    borderBottom: '1px solid #1e1e2e',
    whiteSpace: 'nowrap',
  },
  trEven: { backgroundColor: '#11111b' },
  trOdd: { backgroundColor: '#181825' },
  suggestions: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
    alignItems: 'center',
    marginTop: 4,
  },
  sugLabel: { fontSize: 11 },
  sugItem: {
    backgroundColor: '#1e1e2e',
    color: '#6c7086',
    fontSize: 11,
    padding: '2px 8px',
    borderRadius: 10,
    border: '1px solid #313244',
    cursor: 'pointer',
    transition: 'border-color 0.15s',
  },
};
