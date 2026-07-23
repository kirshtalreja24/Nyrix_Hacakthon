import { useScrollEntry } from '../lib/hooks';
import {
  PieChart as RePieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

const PALETTE = ['#111111', '#787774', '#C4C0BA', '#E1F3FE', '#FDEBEC', '#EDF3EC', '#FBF3DB'];

export default function PieChart({ data, insight, title }) {
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
        <div className="flex flex-col md:flex-row items-center gap-6">
          <ResponsiveContainer width="100%" height={300}>
            <RePieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={110}
                paddingAngle={2}
                dataKey={metricKey}
                nameKey={labelKey}
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: '#FFFFFF',
                  border: '1px solid #EAEAEA',
                  borderRadius: 6,
                  fontSize: 13,
                }}
              />
            </RePieChart>
          </ResponsiveContainer>
        </div>
        {insight && (
          <p className="mt-4 pt-4 border-t border-border text-sm text-text-secondary leading-relaxed">
            {insight}
          </p>
        )}
      </div>
    </div>
  );
}
