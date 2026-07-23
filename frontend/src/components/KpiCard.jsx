import { useScrollEntry } from '../lib/hooks';

export default function KpiCard({ data, insight }) {
  const ref = useScrollEntry();
  if (!data || data.length === 0) return null;

  const row = data[0];
  const metricKeys = Object.keys(row).filter(k =>
    typeof row[k] === 'number'
  );

  return (
    <div ref={ref} className="scroll-entry">
      <div className="bg-surface border border-border rounded-card p-8">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-8">
          {metricKeys.map(key => (
            <div key={key}>
              <p className="text-xs uppercase tracking-widest text-text-secondary font-sans mb-2">
                {key.replace(/_/g, ' ')}
              </p>
              <p className="text-3xl md:text-4xl font-editorial tracking-tight text-text-primary">
                {formatNumber(row[key])}
              </p>
            </div>
          ))}
        </div>
        {insight && (
          <p className="mt-6 pt-6 border-t border-border text-sm text-text-secondary leading-relaxed">
            {insight}
          </p>
        )}
      </div>
    </div>
  );
}

function formatNumber(n) {
  if (n == null) return '--';
  if (typeof n !== 'number') return String(n);
  if (Math.abs(n) >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n % 1 === 0 ? String(n) : n.toFixed(1);
}
