import { useState, useEffect, useRef } from 'react';
import { getAnomalies } from '../lib/api';

export default function AnomalyBanner({ isDataReady }) {
  const [anomalies, setAnomalies] = useState([]);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const hasLoaded = useRef(false);

  useEffect(() => {
    if (isDataReady && !hasLoaded.current) {
      hasLoaded.current = true;
      loadAnomalies();
    }
    // Reset so anomalies reload when data source changes
    if (!isDataReady) {
      hasLoaded.current = false;
      setAnomalies([]);
    }
  }, [isDataReady]);

  async function loadAnomalies() {
    setLoading(true);
    try {
      const data = await getAnomalies();
      console.log('Anomalies loaded:', data);
      setAnomalies(data.anomalies || []);
    } catch (err) {
      console.error('Failed to load anomalies:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading || anomalies.length === 0) return null;

  const highSeverity = anomalies.filter(a => a.severity === 'high');

  return (
    <div className="mb-6 animate-fade-in">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 rounded-card border border-pale-yellow-text/20
          bg-pale-yellow transition-all hover:border-pale-yellow-text/30"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-base">⚠</span>
            <div>
              <span className="text-sm font-sans font-medium text-pale-yellow-text">
                {anomalies.length} anomal{anomalies.length === 1 ? 'y' : 'ies'} detected
              </span>
              {highSeverity.length > 0 && (
                <span className="text-xs text-pale-red-text ml-2 font-mono">
                  ({highSeverity.length} high severity)
                </span>
              )}
            </div>
          </div>
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            className={`text-pale-yellow-text transition-transform ${expanded ? 'rotate-180' : ''}`}
          >
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="mt-2 space-y-2 animate-fade-in">
          {anomalies.map((a, i) => (
            <div
              key={i}
              className="px-4 py-3 rounded-card border border-border bg-surface"
            >
              <div className="flex items-center gap-3 mb-1.5">
                <span className={`text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-card
                  ${a.severity === 'high'
                    ? 'bg-pale-red text-pale-red-text'
                    : 'bg-pale-yellow text-pale-yellow-text'
                  }`}
                >
                  {a.severity}
                </span>
                <span className="text-xs font-mono text-text-secondary">
                  {a.entity}
                </span>
                <span className="text-xs font-mono text-text-muted">→</span>
                <span className="text-xs font-sans text-text-primary">
                  {a.metric?.replace('_', ' ')}
                </span>
                <span className={`text-xs font-mono font-medium
                  ${a.change_pct < 0 ? 'text-pale-red-text' : 'text-pale-green-text'}`}
                >
                  {a.change_pct > 0 ? '+' : ''}{a.change_pct}%
                </span>
              </div>
              {a.explanation && (
                <p className="text-xs text-text-secondary leading-relaxed">
                  {a.explanation}
                </p>
              )}
              <p className="text-[10px] text-text-muted font-mono mt-1.5">
                {a.week?.startsWith('week') ? a.week : `Week of ${a.week}`}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
