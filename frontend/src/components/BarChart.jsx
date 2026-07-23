import { useScrollEntry } from '../lib/hooks';
import {
  BarChart as ReBarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const PALETTE = ['#111111', '#787774', '#C4C0BA', '#E1F3FE', '#FDEBEC', '#EDF3EC', '#FBF3DB'];

export default function BarChart({ data, insight, title }) {
  const ref = useScrollEntry();
  if (!data || data.length === 0) return null;

  const keys = Object.keys(data[0]);
  const labelKey = keys.find(k => typeof data[0][k] === 'string') || keys[0];
  const metricKey = keys.find(k => typeof data[0][k] === 'number') || keys[1];

  return (
    <div ref={ref} className="scroll-entry">
      <div className="bg-surface border border-border rounded-card p-6">
        {title && (
          <h3 className="text-sm font-sans uppercase tracking-widest text-text-secondary mb-4">
            {title}
          </h3>
        )}
        <ResponsiveContainer width="100%" height={320}>
          <ReBarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <XAxis
              dataKey={labelKey}
              tick={{ fontSize: 12, fill: '#787774', fontFamily: 'system-ui' }}
              axisLine={{ stroke: '#EAEAEA' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#787774', fontFamily: 'system-ui' }}
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
                fontFamily: 'system-ui',
              }}
              cursor={{ fill: 'rgba(0,0,0,0.02)' }}
            />
            <Bar dataKey={metricKey} radius={[4, 4, 0, 0]} maxBarSize={48}>
              {data.map((_, i) => (
                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Bar>
          </ReBarChart>
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
