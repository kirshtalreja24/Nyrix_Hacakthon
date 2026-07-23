import { useState } from 'react';

const EXAMPLES = [
  'Which branch had the lowest revenue last month?',
  'Compare average order value across all locations this quarter.',
  'Which menu item is underperforming in Karachi but doing well in Lahore?',
  'Show revenue trend for LHR-01 over the last 8 weeks.',
  'What\'s each branch\'s share of total revenue this month?',
  'Flag any branch where footfall dropped more than 20% week-over-week.',
];

export default function QueryBox({ onSubmit, loading, disabled }) {
  const [value, setValue] = useState('');

  function handleSubmit(e) {
    e.preventDefault();
    if (!value.trim() || loading) return;
    onSubmit(value.trim());
  }

  function handleExampleClick(q) {
    setValue(q);
    onSubmit(q);
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className="relative">
        <div className="bg-surface border border-border rounded-card overflow-hidden
          transition-all focus-within:border-text-primary/30">
          <textarea
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="Ask a question about your business data..."
            disabled={disabled || loading}
            rows={2}
            className="w-full px-6 py-4 text-sm font-sans bg-transparent resize-none
              placeholder:text-text-muted focus:outline-none disabled:opacity-50"
          />
          <div className="flex items-center justify-between px-6 py-3 border-t border-border/50">
            <div className="flex items-center gap-2 text-xs text-text-muted">
              <kbd>Enter</kbd>
              <span>to submit</span>
            </div>
            <button
              type="submit"
              disabled={!value.trim() || loading || disabled}
              className="px-5 py-2 text-xs font-sans uppercase tracking-wider bg-text-primary
                text-white rounded-card hover:bg-text-primary/80 transition-all
                active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed"
            >
              {loading ? 'Thinking...' : 'Query'}
            </button>
          </div>
        </div>
      </form>

      {/* Example queries */}
      <div className="mt-4 flex flex-wrap gap-2">
        {EXAMPLES.map((q, i) => (
          <button
            key={i}
            onClick={() => handleExampleClick(q)}
            disabled={loading || disabled}
            className="text-xs px-3 py-1.5 rounded-card border border-border bg-surface
              text-text-secondary hover:text-text-primary hover:border-text-primary/20
              transition-all font-sans disabled:opacity-40"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
