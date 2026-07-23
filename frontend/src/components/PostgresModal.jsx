import { useState } from 'react';

export default function PostgresModal({ open, onClose, onConnect, loading, error }) {
  const [form, setForm] = useState({
    host: '',
    port: '5432',
    dbname: '',
    user: '',
    password: '',
  });

  function handleChange(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!form.host || !form.dbname || !form.user) return;
    onConnect(form);
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-surface border border-border rounded-card shadow-lift
        w-full max-w-md mx-4 overflow-hidden animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-border">
          <div>
            <h3 className="text-base font-editorial tracking-tight text-text-primary">
              Connect to PostgreSQL
            </h3>
            <p className="text-xs text-text-muted font-mono mt-1">
              Enter your database credentials
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

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-6 space-y-4">
          {/* Host */}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-text-secondary mb-1.5">
              Host
            </label>
            <input
              type="text"
              name="host"
              value={form.host}
              onChange={handleChange}
              placeholder="db.example.supabase.co"
              required
              className="w-full px-4 py-2.5 text-sm font-sans bg-canvas border border-border rounded-card
                text-text-primary placeholder:text-text-muted focus:outline-none focus:border-text-primary/30
                transition-all"
            />
          </div>

          {/* Port */}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-text-secondary mb-1.5">
              Port
            </label>
            <input
              type="text"
              name="port"
              value={form.port}
              onChange={handleChange}
              placeholder="5432"
              className="w-full px-4 py-2.5 text-sm font-sans bg-canvas border border-border rounded-card
                text-text-primary placeholder:text-text-muted focus:outline-none focus:border-text-primary/30
                transition-all"
            />
          </div>

          {/* Database Name */}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-text-secondary mb-1.5">
              Database Name
            </label>
            <input
              type="text"
              name="dbname"
              value={form.dbname}
              onChange={handleChange}
              placeholder="postgres"
              required
              className="w-full px-4 py-2.5 text-sm font-sans bg-canvas border border-border rounded-card
                text-text-primary placeholder:text-text-muted focus:outline-none focus:border-text-primary/30
                transition-all"
            />
          </div>

          {/* User */}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-text-secondary mb-1.5">
              User
            </label>
            <input
              type="text"
              name="user"
              value={form.user}
              onChange={handleChange}
              placeholder="postgres"
              required
              className="w-full px-4 py-2.5 text-sm font-sans bg-canvas border border-border rounded-card
                text-text-primary placeholder:text-text-muted focus:outline-none focus:border-text-primary/30
                transition-all"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-text-secondary mb-1.5">
              Password
            </label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder="your-password"
              className="w-full px-4 py-2.5 text-sm font-sans bg-canvas border border-border rounded-card
                text-text-primary placeholder:text-text-muted focus:outline-none focus:border-text-primary/30
                transition-all"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 rounded-card bg-pale-red border border-pale-red-text/20
              text-xs text-pale-red-text leading-relaxed">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-sans uppercase tracking-wider rounded-card
                border border-border text-text-secondary hover:text-text-primary
                hover:border-text-primary/20 transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !form.host || !form.dbname || !form.user}
              className="px-5 py-2 text-xs font-sans uppercase tracking-wider rounded-card
                bg-text-primary text-white hover:bg-text-primary/80 transition-all
                active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed"
            >
              {loading ? 'Connecting...' : 'Connect'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
