import { useState, useEffect } from 'react';
import { getStatus, uploadCSV, connectPostgres, runQuery, getExecutiveSummary, getSuggestions, clearCSV, disconnectPostgres } from './lib/api';
import ExecutiveSummary from './components/ExecutiveSummary';
import QueryBox from './components/QueryBox';
import ResultFeed from './components/ResultFeed';
import PostgresModal from './components/PostgresModal';
import DataPreview from './components/DataPreview';
import AnomalyBanner from './components/AnomalyBanner';
import ExportButton from './components/ExportButton';

function generateSessionId() {
  return 'session_' + Math.random().toString(36).substring(2, 10) + '_' + Date.now();
}

export default function App() {
  const [sourceStatus, setSourceStatus] = useState(null);
  const [executiveSummary, setExecutiveSummary] = useState(null);
  const [execSummaryLoading, setExecSummaryLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [queryLoading, setQueryLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [postgresModalOpen, setPostgresModalOpen] = useState(false);
  const [postgresConnecting, setPostgresConnecting] = useState(false);
  const [postgresError, setPostgresError] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewSource, setPreviewSource] = useState('csv');
  const [sessionId] = useState(() => generateSessionId());
  const [suggestions, setSuggestions] = useState([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);

  const isDataReady = sourceStatus &&
    ((sourceStatus.csv && sourceStatus.csv.loaded) ||
     (sourceStatus.postgres && sourceStatus.postgres.connected));

  useEffect(() => {
    checkStatus();
  }, []);

  useEffect(() => {
    if (isDataReady) {
      loadSuggestions();
    } else {
      setSuggestions([]);
    }
  }, [isDataReady, results.length]);

  const checkStatus = async () => {
    try {
      const status = await getStatus();
      setSourceStatus(status);
    } catch (err) {
      console.error('Status check failed:', err);
    }
  };

  const handleCSVUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadStatus('loading');
    try {
      const result = await uploadCSV(file);
      setUploadStatus('success');
      checkStatus();
      setPreviewSource('csv');
      setPreviewOpen(true);
    } catch (err) {
      setUploadStatus('error');
      setError(err.message);
    }
  };

  const handlePostgresConnect = async (config) => {
    setPostgresConnecting(true);
    setPostgresError(null);
    try {
      const result = await connectPostgres(config);
      if (result.connected === false) {
        setPostgresError(result.error || result.hint || 'Connection failed');
        return;
      }
      setPostgresModalOpen(false);
      setUploadStatus('success');
      checkStatus();
      setPreviewSource('postgres');
      setPreviewOpen(true);
    } catch (err) {
      setPostgresError(err.message);
    } finally {
      setPostgresConnecting(false);
    }
  };

  const handlePreviewConfirm = () => {
    refreshSummary();
  };

  const refreshSummary = async () => {
    setExecSummaryLoading(true);
    try {
      const summary = await getExecutiveSummary();
      setExecutiveSummary(summary);
    } catch (err) {
      setExecutiveSummary({ error: err.message });
    } finally {
      setExecSummaryLoading(false);
    }
  };

  const loadSuggestions = async () => {
    setSuggestionsLoading(true);
    try {
      const res = await getSuggestions(results.length > 0 ? sessionId : null);
      setSuggestions(res.suggestions || []);
    } catch (err) {
      console.error('Failed to load suggestions:', err);
    } finally {
      setSuggestionsLoading(false);
    }
  };

  const handleClearCSV = async () => {
    try {
      await clearCSV();
      checkStatus();
      setResults([]);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDisconnectPostgres = async () => {
    try {
      await disconnectPostgres();
      checkStatus();
      setResults([]);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleQuery = async (question) => {
    setQueryLoading(true);
    setError(null);
    try {
      const result = await runQuery(question, sessionId);
      setResults(prev => [...prev, result]);
    } catch (err) {
      setError(err.message);
    } finally {
      setQueryLoading(false);
    }
  };


  const allBranches = [...new Set(
    results.flatMap(r => (r.chart_data || []).map(d => d.branch).filter(Boolean))
  )];

  return (
    <div className="min-h-screen bg-canvas">
      {/* Ambient background blob */}
      <div
        className="fixed inset-0 pointer-events-none animate-ambient"
        style={{
          background: 'radial-gradient(ellipse at 30% 20%, rgba(225, 243, 254, 0.04) 0%, transparent 60%), radial-gradient(ellipse at 70% 80%, rgba(253, 235, 236, 0.03) 0%, transparent 60%)',
        }}
      />

      {/* Navbar */}
      <nav className="relative border-b border-border bg-surface/80 backdrop-blur-sm sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-card bg-text-primary flex items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3v18h18"/>
                <path d="M7 16l4-5 4 3 4-6"/>
              </svg>
            </div>
            <span className="text-lg font-editorial tracking-tight text-text-primary">
              Nyrix Analytics
            </span>
          </div>
          <div className="flex items-center gap-3">
            {isDataReady && <ExportButton branchNames={allBranches} />}
          </div>
        </div>
      </nav>

      <div className="relative max-w-5xl mx-auto px-6 py-10 md:py-16">
        {/* Data Sources Bar */}
        <section className="mb-8">
          <div className="bg-surface border border-border rounded-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-sans uppercase tracking-widest text-text-secondary">
                Data Sources
              </h2>
              <div className="flex items-center gap-2">
                {isDataReady && (
                  <span className="text-[10px] font-mono uppercase tracking-wider text-pale-green-text bg-pale-green px-2 py-1 rounded-card">
                    Connected
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* CSV Upload */}
              <div className="flex items-center gap-4 p-4 rounded-card border border-border/50 hover:border-border transition-all">
                <div className="w-10 h-10 rounded-card bg-pale-blue flex items-center justify-center flex-shrink-0">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1F6C9F" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
                    <polyline points="14 2 14 8 20 8"/>
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-sans font-medium text-text-primary">CSV / Excel Upload</p>
                  <p className="text-xs text-text-muted mt-0.5">
                    {sourceStatus?.csv?.loaded
                      ? (() => {
                          const tables = Object.keys(sourceStatus.csv).filter(k => k.endsWith('_rows'));
                          const totalRows = tables.reduce((sum, k) => sum + (sourceStatus.csv[k] || 0), 0);
                          return `${totalRows.toLocaleString()} rows loaded`;
                        })()
                      : 'Upload any CSV file'}
                  </p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <label className="cursor-pointer">
                    <input type="file" accept=".csv,.xlsx" className="hidden" onChange={handleCSVUpload} />
                    <span className="text-xs font-sans uppercase tracking-wider px-3 py-2 rounded-card
                      border border-border text-text-secondary hover:text-text-primary hover:border-text-primary/30 transition-all">
                      Upload
                    </span>
                  </label>
                  {sourceStatus?.csv?.loaded && (
                    <button
                      onClick={handleClearCSV}
                      className="text-xs font-sans uppercase tracking-wider px-2 py-2 rounded-card
                        border border-pale-red-text/20 text-pale-red-text hover:bg-pale-red
                        transition-all flex-shrink-0"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>

              {/* PostgreSQL */}
              <div className="flex items-center gap-4 p-4 rounded-card border border-border/50 hover:border-border transition-all">
                <div className="w-10 h-10 rounded-card bg-pale-green flex items-center justify-center flex-shrink-0">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#346538" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <ellipse cx="12" cy="5" rx="9" ry="3"/>
                    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-sans font-medium text-text-primary">PostgreSQL Database</p>
                  <p className="text-xs text-text-muted mt-0.5">
                    {sourceStatus?.postgres?.connected
                      ? (() => {
                          const tables = Object.keys(sourceStatus.postgres).filter(k => k.endsWith('_rows'));
                          const totalRows = tables.reduce((sum, k) => sum + (sourceStatus.postgres[k] || 0), 0);
                          return `${tables.length} table${tables.length !== 1 ? 's' : ''}, ${totalRows.toLocaleString()} rows`;
                        })()
                      : 'Connect to a live PostgreSQL instance'}
                  </p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button
                    onClick={() => setPostgresModalOpen(true)}
                    disabled={uploadStatus === 'loading'}
                    className="text-xs font-sans uppercase tracking-wider px-3 py-2 rounded-card
                      border border-border text-text-secondary hover:text-text-primary hover:border-text-primary/30 transition-all
                      disabled:opacity-40 flex-shrink-0"
                  >
                    Connect
                  </button>
                  {sourceStatus?.postgres?.connected && (
                    <button
                      onClick={handleDisconnectPostgres}
                      className="text-xs font-sans uppercase tracking-wider px-2 py-2 rounded-card
                        border border-pale-red-text/20 text-pale-red-text hover:bg-pale-red
                        transition-all flex-shrink-0"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Anomaly Banner */}
        <AnomalyBanner isDataReady={isDataReady} />

        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 rounded-card bg-pale-red border border-pale-red-text/20 text-sm text-pale-red-text flex items-start gap-3">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0 mt-0.5">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <span className="flex-1">{error}</span>
            <button onClick={() => setError(null)} className="text-pale-red-text/60 hover:text-pale-red-text">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        )}

        {/* Executive Summary */}
        <section className="mb-8">
          <ExecutiveSummary
            data={executiveSummary}
            loading={execSummaryLoading}
            onRefresh={refreshSummary}
          />
        </section>

        {/* Query Box */}
        <section className="mb-8">
          <QueryBox
            onSubmit={handleQuery}
            loading={queryLoading || suggestionsLoading}
            disabled={!isDataReady}
            hasResults={results.length > 0}
            suggestions={suggestions}
          />
        </section>

        {/* Results Feed */}
        <section>
          <ResultFeed results={results} />
        </section>

        {/* Footer */}
        <footer className="mt-20 pt-8 border-t border-border">
          <div className="flex items-center justify-between text-xs text-text-muted font-mono">
            <span>Nyrix Analytics v1.0</span>
            <span>Business Analytics Assistant</span>
          </div>
        </footer>
      </div>

      {/* PostgreSQL Connection Modal */}
      <PostgresModal
        open={postgresModalOpen}
        onClose={() => { setPostgresModalOpen(false); setPostgresError(null); }}
        onConnect={handlePostgresConnect}
        loading={postgresConnecting}
        error={postgresError}
      />

      {/* Data Preview Modal */}
      <DataPreview
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        sourceType={previewSource}
        onConfirm={handlePreviewConfirm}
      />
    </div>
  );
}
