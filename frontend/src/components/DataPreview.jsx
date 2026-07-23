import { useState, useEffect } from 'react';
import { getSourcePreview } from '../lib/api';

export default function DataPreview({ open, onClose, sourceType, onConfirm }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (open && sourceType) {
      loadPreview();
    }
  }, [open, sourceType]);

  async function loadPreview() {
    setLoading(true);
    setError('');
    try {
      const result = await getSourcePreview(sourceType);
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  const tables = data?.tables || (data ? [data] : []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-surface border border-border rounded-card shadow-lift
        w-full max-w-3xl mx-4 max-h-[85vh] overflow-hidden animate-fade-in flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-border flex-shrink-0">
          <div>
            <h3 className="text-base font-editorial tracking-tight text-text-primary">
              Data Preview
            </h3>
            <p className="text-xs text-text-muted font-mono mt-1">
              {sourceType === 'csv' ? 'CSV / DuckDB' : 'PostgreSQL'} — verify your data before querying
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-card flex items-center justify-center
              text-text-muted hover:text-text-primary hover:bg-canvas transition-all"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading ? (
            <div className="text-center py-12 text-sm text-text-muted font-mono">Loading preview...</div>
          ) : error ? (
            <div className="p-4 rounded-card bg-pale-red border border-pale-red-text/20
              text-sm text-pale-red-text">
              {error}
            </div>
          ) : tables.length === 0 ? (
            <div className="text-center py-12 text-sm text-text-muted">No data to preview.</div>
          ) : (
            <div className="space-y-6">
              {tables.map((tbl, idx) => (
                <div key={idx}>
                  {/* Table info bar */}
                  <div className="flex items-center gap-4 mb-4">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-pale-green-text" />
                      <span className="text-sm font-sans font-medium text-text-primary">
                        {tbl.table_name}
                      </span>
                    </div>
                    <span className="text-xs font-mono text-text-muted">
                      {tbl.row_count?.toLocaleString()} rows
                    </span>
                    <span className="text-xs font-mono text-text-muted">
                      {tbl.columns?.length} columns
                    </span>
                  </div>

                  {/* Column types */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {tbl.columns?.map(col => (
                      <span
                        key={col.name}
                        className="text-[10px] font-mono px-2 py-1 rounded-card bg-canvas
                          border border-border text-text-secondary"
                      >
                        {col.name} <span className="text-text-muted">({col.type})</span>
                      </span>
                    ))}
                  </div>

                  {/* Sample data table */}
                  {tbl.sample_rows && tbl.sample_rows.length > 0 && (
                    <div className="overflow-x-auto rounded-card border border-border">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="bg-canvas">
                            {tbl.columns?.map(col => (
                              <th
                                key={col.name}
                                className="px-3 py-2 text-left font-mono font-medium text-text-secondary
                                  border-b border-border whitespace-nowrap"
                              >
                                {col.name}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {tbl.sample_rows.map((row, ri) => (
                            <tr key={ri} className="border-b border-border/50 last:border-0">
                              {tbl.columns?.map(col => (
                                <td
                                  key={col.name}
                                  className="px-3 py-2 text-text-primary font-sans whitespace-nowrap"
                                >
                                  {row[col.name] !== null && row[col.name] !== undefined
                                    ? String(row[col.name])
                                    : '—'}
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
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border flex items-center justify-end flex-shrink-0">
          <button
            onClick={() => { onConfirm(); onClose(); }}
            disabled={loading || !!error}
            className="px-6 py-2.5 text-xs font-sans uppercase tracking-wider bg-text-primary
              text-white rounded-card hover:bg-text-primary/80 transition-all
              active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Looks good, continue →
          </button>
        </div>
      </div>
    </div>
  );
}
