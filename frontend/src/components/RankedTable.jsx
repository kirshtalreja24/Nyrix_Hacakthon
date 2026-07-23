import { useScrollEntry } from '../lib/hooks';

export default function RankedTable({ data, insight, title }) {
  const ref = useScrollEntry();
  if (!data || data.length === 0) return null;

  // Sort by the primary numeric column descending
  const keys = Object.keys(data[0]);
  const metricKey = keys.find(k => typeof data[0][k] === 'number') || keys[keys.length - 1];
  const sorted = [...data].sort((a, b) => (b[metricKey] || 0) - (a[metricKey] || 0));

  return (
    <div ref={ref} className="scroll-entry">
      <div className="bg-surface border border-border rounded-card overflow-hidden">
        {title && (
          <div className="px-6 pt-6 pb-0">
            <h3 className="text-sm font-sans uppercase tracking-widest text-text-secondary mb-4">
              {title}
            </h3>
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-6 py-3 font-mono text-xs text-text-muted uppercase tracking-wider">
                  #
                </th>
                {keys.map(key => (
                  <th
                    key={key}
                    className="text-left px-6 py-3 font-mono text-xs text-text-muted uppercase tracking-wider"
                  >
                    {key.replace(/_/g, ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((row, i) => (
                <tr
                  key={i}
                  className="border-b border-border/50 hover:bg-canvas transition-colors"
                >
                  <td className="px-6 py-3 font-mono text-text-muted">{i + 1}</td>
                  {keys.map(key => (
                    <td key={key} className="px-6 py-3 font-sans">
                      {typeof row[key] === 'number'
                        ? row[key].toLocaleString()
                        : row[key]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {insight && (
          <p className="px-6 py-4 border-t border-border text-sm text-text-secondary leading-relaxed">
            {insight}
          </p>
        )}
      </div>
    </div>
  );
}
