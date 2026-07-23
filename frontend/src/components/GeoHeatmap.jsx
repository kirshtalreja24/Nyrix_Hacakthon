import { useScrollEntry } from '../lib/hooks';

export default function GeoHeatmap({ data, insight, title }) {
  const ref = useScrollEntry();
  if (!data || data.length === 0) return null;

  const keys = Object.keys(data[0]);
  const branchKey = keys.find(k => k === 'branch') || keys[0];
  const cityKey = keys.find(k => k === 'city') || keys[1];
  const metricKey = keys.find(k => typeof data[0][k] === 'number') || keys[keys.length - 1];

  // Group by city
  const cities = [...new Set(data.map(d => d[cityKey]))];
  const branches = [...new Set(data.map(d => d[branchKey]))];

  // Compute min/max for color scaling
  const values = data.map(d => d[metricKey] || 0);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;

  function getIntensity(val) {
    const t = (val - minVal) / range;
    // Scale from pale blue to deep charcoal
    const r = Math.round(225 - t * 190);
    const g = Math.round(243 - t * 210);
    const b = Math.round(254 - t * 210);
    return `rgb(${r}, ${g}, ${b})`;
  }


  function getTextColor(val) {
    const t = (val - minVal) / range;
    return t > 0.6 ? '#FFFFFF' : '#111111';
  }

  return (
    <div ref={ref} className="scroll-entry">
      <div className="bg-surface border border-border rounded-card p-6">
        {title && (
          <h3 className="text-sm font-sans uppercase tracking-widest text-text-secondary mb-4">
            {title}
          </h3>
        )}
        <div className="mb-2">
          <p className="text-xs font-mono text-text-muted">
            Geographic Heatmap — color intensity by {metricKey.replace(/_/g, ' ')}
          </p>
        </div>
        <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${cities.length}, 1fr)` }}>
          {/* Header row */}
          {cities.map(city => (
            <div
              key={city}
              className="text-center py-2 font-sans text-xs font-medium text-text-secondary uppercase tracking-wider border-b border-border"
            >
              {city}
            </div>
          ))}
          {/* Data rows */}
          {branches.map(branch => (
            <div key={branch} className="contents">
              {cities.map(city => {
                const cell = data.find(d => d[branchKey] === branch && d[cityKey] === city);
                const val = cell ? (cell[metricKey] || 0) : 0;
                return (
                  <div
                    key={`${branch}-${city}`}
                    className="rounded-card p-4 text-center transition-all"
                    style={{
                      backgroundColor: getIntensity(val),
                      color: getTextColor(val),
                    }}
                  >
                    <p className="text-xs font-medium opacity-80">{branch}</p>
                    <p className="text-lg font-editorial tracking-tight">
                      {typeof val === 'number' ? val.toLocaleString() : val}
                    </p>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        {/* Legend */}
        <div className="flex items-center gap-2 mt-4 justify-end">
          <span className="text-xs font-mono text-text-muted">Low</span>
          <div className="w-24 h-2 rounded-full" style={{
            background: `linear-gradient(to right, ${getIntensity(minVal)}, ${getIntensity(maxVal)})`,
          }} />
          <span className="text-xs font-mono text-text-muted">High</span>
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
