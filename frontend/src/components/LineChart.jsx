import { useScrollEntry } from '../lib/hooks';
import {
  LineChart as ReLineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const PALETTE = ['#111111', '#787774', '#C4C0BA', '#E1F3FE', '#FDEBEC', '#EDF3EC'];

export default function LineChart({ data, insight, title }) {
  const ref = useScrollEntry();
  if (!data || data.length === 0) return null;

  const keys = Object.keys(data[0]);
  const timeKey = keys.find(k => ['date', 'week_start', 'month', 'year'].includes(k)) || keys[0];
  const metricKeys = keys.filter(k => typeof data[0][k] === 'number');

  // If there's a branch/entity column, split into multiple lines
  const entityKey = keys.find(k => ['branch', 'city'].includes(k));
  const entities = entityKey ? [...new Set(data.map(d => d[entityKey]))] : null;

  // Group data for multi-line
  const chartData = data.map(row => ({
    ...row,
    [timeKey]: formatTimeLabel(row[timeKey]),
  }));

  return (
    <div ref={ref} className="scroll-entry">
      <div className="bg-surface border border-border rounded-card p-6">
        {title && (
          <h3 className="text-sm font-sans uppercase tracking-widest text-text-secondary mb-4">
            {title}
          </h3>
        )}
        <ResponsiveContainer width="100%" height={340}>
          <ReLineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <XAxis
              dataKey={timeKey}
              tick={{ fontSize: 11, fill: '#787774', fontFamily: 'system-ui' }}
              axisLine={{ stroke: '#EAEAEA' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#787774', fontFamily: 'system-ui' }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            <Tooltip
              contentStyle={{
                background: '#FFFFFF',
                border: '1px solid #EAEAEA',
                borderRadius: 6,
                fontSize: 13,
              }}
            />
            {entities ? (
              entities.map((entity, i) => {
                const entityData = data
                  .filter(d => d[entityKey] === entity)
                  .map(d => ({ ...d, [timeKey]: formatTimeLabel(d[timeKey]) }));
                // Merge into one dataset by timeKey
                return (
                  <Line
                    key={entity}
                    type="monotone"
                    dataKey={metricKeys[0]}
                    stroke={PALETTE[i % PALETTE.length]}
                    strokeWidth={2}
                    dot={false}
                    data={entityData}
                    name={entity}
                  />
                );
              })
            ) : (
              <Line
                type="monotone"
                dataKey={metricKeys[0]}
                stroke="#111111"
                strokeWidth={2}
                dot={{ r: 3, fill: '#111111' }}
              />
            )}
          </ReLineChart>
        </ResponsiveContainer>
        {insight && (
          <p className="mt-4 pt-4 border-t border-border text-sm text-text-secondary leading-relaxed">
            {insight}
          </p>
        )}
      </div>
    </div>
  );
}

function formatTimeLabel(val) {
  if (!val) return '';
  if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(val)) {
    const d = new Date(val + 'T00:00:00');
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
  return String(val);
}
