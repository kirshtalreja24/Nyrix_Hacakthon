import { useState } from 'react';
import { exportReport } from '../lib/api';

export default function ExportButton({ branchNames = [] }) {
  const [scope, setScope] = useState('all');
  const [branch, setBranch] = useState('');
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  async function handleExport() {
    setLoading(true);
    try {
      const blob = await exportReport(scope, scope === 'branch' ? branch : null);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics_report_${scope}${branch ? '_' + branch : ''}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Export failed: ' + err.message);
    } finally {
      setLoading(false);
      setShowDropdown(false);
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="text-xs font-sans uppercase tracking-wider px-3 py-2 rounded-card
          border border-border text-text-secondary hover:text-text-primary
          hover:border-text-primary/20 transition-all flex items-center gap-2"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        Export
      </button>

      {showDropdown && (
        <div className="absolute right-0 top-full mt-2 w-64 bg-surface border border-border
          rounded-card shadow-lift overflow-hidden animate-fade-in z-40">
          <div className="p-4 space-y-3">
            <label className="block text-xs font-mono uppercase tracking-wider text-text-secondary">
              Report Scope
            </label>
            <select
              value={scope}
              onChange={(e) => { setScope(e.target.value); setBranch(''); }}
              className="w-full px-3 py-2 text-sm font-sans bg-canvas border border-border rounded-card
                text-text-primary focus:outline-none focus:border-text-primary/30 transition-all"
            >
              <option value="all">All Branches</option>
              <option value="branch">Single Branch</option>
            </select>

            {scope === 'branch' && (
              <select
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                className="w-full px-3 py-2 text-sm font-sans bg-canvas border border-border rounded-card
                  text-text-primary focus:outline-none focus:border-text-primary/30 transition-all"
              >
                <option value="">Select a branch...</option>
                {branchNames.map(name => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            )}

            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={() => setShowDropdown(false)}
                className="flex-1 px-3 py-2 text-xs font-sans uppercase tracking-wider rounded-card
                  border border-border text-text-secondary hover:text-text-primary
                  hover:border-text-primary/20 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleExport}
                disabled={loading || (scope === 'branch' && !branch)}
                className="flex-1 px-3 py-2 text-xs font-sans uppercase tracking-wider rounded-card
                  bg-text-primary text-white hover:bg-text-primary/80 transition-all
                  active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {loading ? 'Generating...' : 'Download PDF'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
