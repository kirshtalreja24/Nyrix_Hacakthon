import { useState } from 'react';
import { useScrollEntry } from '../lib/hooks';

export default function ExecutiveSummary({ data, loading, onRefresh }) {
  const ref = useScrollEntry();

  return (
    <div ref={ref} className="scroll-entry">
      <div className="bg-surface border border-border rounded-card overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-8 py-5 border-b border-border">
          <div>
            <h2 className="text-lg font-editorial tracking-tight text-text-primary">
              Executive Summary
            </h2>
            <p className="text-xs text-text-muted font-mono mt-1">
              {data?.generated_at
                ? `Generated ${formatTimestamp(data.generated_at)}`
                : 'Standing multi-branch synthesis'}
            </p>
          </div>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 text-xs font-sans uppercase tracking-wider
              border border-border rounded-card text-text-secondary hover:text-text-primary
              hover:border-text-primary/20 transition-all disabled:opacity-40"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
              className={loading ? 'animate-spin' : ''}
            >
              <path d="M21 12a9 9 0 1 1-6.22-8.56"/>
              <path d="M21 3v9h-9"/>
            </svg>
            {loading ? 'Generating...' : 'Refresh'}
          </button>
        </div>

        {/* Content */}
        <div className="px-8 py-6">
          {loading && !data && (
            <div className="space-y-3">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-5 bg-canvas rounded-card animate-pulse" style={{ width: `${70 + i * 8}%` }} />
              ))}
            </div>
          )}

          {!loading && data?.summary_bullets && (
            <ul className="space-y-4">
              {data.summary_bullets.map((bullet, i) => (
                <li key={i} className="flex gap-3 text-sm leading-relaxed text-text-primary">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-canvas border border-border
                    flex items-center justify-center text-[10px] font-mono text-text-muted mt-0.5">
                    {i + 1}
                  </span>
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          )}

          {!loading && data?.error && (
            <p className="text-sm text-pale-red-text bg-pale-red rounded-card p-4">
              {data.error}
            </p>
          )}

          {!loading && !data && (
            <p className="text-sm text-text-muted">
              No data loaded. Connect to a data source to generate the Executive Summary.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function formatTimestamp(ts) {
  try {
    const d = new Date(ts);
    return d.toLocaleString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

