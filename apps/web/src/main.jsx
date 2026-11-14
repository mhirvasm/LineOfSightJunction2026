import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import targets from '../../../contracts/targets.json';
import './styles.css';

const money = (record) => record?.total_minor == null ? 'Unreadable' :
  new Intl.NumberFormat('en-IE', { style: 'currency', currency: record.currency }).format(record.total_minor / 100);

function Receipt({ record, targetId }) {
  if (!record) return <div className="empty"><span className="empty-icon" aria-hidden="true">—</span><p>No applied receipt</p><small>Previewing a receipt does not update a draft.</small></div>;
  if (targetId === 'json') return <pre>{JSON.stringify(record, null, 2)}</pre>;
  const fields = [
    ['Merchant', record.merchant ?? 'Needs review'], ['Date', record.date ?? 'Needs review'],
    ['Total', money(record)], ['Currency', record.currency],
    ['Tax', record.tax_minor == null ? 'Not provided (optional)' : money({ ...record, total_minor: record.tax_minor })],
  ];
  return <dl className="receipt-fields">{fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function TargetShell({ targetId, snapshots, health, healthError }) {
  const target = targets[targetId];
  const initial = new URLSearchParams(window.location.search).get('fixture');
  const [fixtureId, setFixtureId] = useState(initial in snapshots ? initial : `PREVIEW_${targetId}`);
  const snapshot = snapshots[fixtureId];
  const selected = snapshot.target_id === targetId;
  const preview = selected ? snapshot.receipt : null;

  useEffect(() => { document.title = `${target.label} · LineOfSight`; }, [target.label]);

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="/expense"><span className="brand-mark" aria-hidden="true">L<span>•</span></span>LineOfSight</a><nav aria-label="Destinations">{Object.entries(targets).map(([id, item]) => <a key={id} href={item.route} aria-current={id === targetId ? 'page' : undefined}>{item.label}</a>)}</nav><span className="mode-badge">FIXTURE MODE</span></header>
    <main>
      <div className="page-heading"><div><p className="eyebrow">REGISTERED DESTINATION / {String(target.marker_id).padStart(2, '0')}</p><h1>{target.label}</h1><p className="subtitle">Look here. Review the receipt. Confirm deliberately.</p></div><div className="hub-status" role="status"><span className={health ? 'status-dot online' : 'status-dot'} />{health ? 'Hub reachable' : 'Hub unavailable'}<small>{health ? 'Fixture UI · WebSocket not connected' : healthError}</small></div></div>
      <div className="fixture-notice"><strong>Predetermined sample data</strong><span>These are UI examples. Camera input, extraction, and transfers are not connected.</span></div>
      <div className="workspace">
        <section className="marker-panel" aria-label={`${target.label} target marker`}><div className="panel-top"><span>YOUR TARGET</span><span>MARKER {target.marker_id}</span></div><div className="marker-tile"><img src={target.marker_asset} alt={`ArUco DICT_4X4_50 marker ${target.marker_id}`} width="600" height="600" /></div><h2>{target.label}</h2><p>Keep this marker visible to the glasses.</p><span className="dictionary">DICT_4X4_50 · ID {target.marker_id}</span></section>
        <div className="data-column">
          <section className="card preview-card"><div className="card-title"><h2>Receipt preview</h2><span className="state-chip">{snapshot.state}</span></div><p className="feedback">{snapshot.feedback}</p>{preview ? <><div className="preview-total">{money(preview)}</div><p className="preview-merchant">{preview.merchant ?? 'Merchant needs review'} · {preview.date ?? 'Date needs review'}</p></> : <p className="muted">{snapshot.receipt ? 'This example is directed to another destination.' : 'No active receipt in this example.'}</p>}<div className="preview-footer">Sample only · no confirmation action is connected</div></section>
          <section className="card applied-card"><div className="card-title"><h2>Applied {targetId === 'json' ? 'JSON' : 'expense draft'}</h2><span className="read-only">READ ONLY</span></div><Receipt record={snapshot.drafts[targetId]} targetId={targetId} /></section>
        </div>
      </div>
      <section className="fixture-controls" aria-label="Fixture examples"><div><h2>UI fixture examples</h2><p>Changes the local example only. Does not change hub memory.</p></div><label>Example state<select value={fixtureId} onChange={(event) => setFixtureId(event.target.value)}>{Object.entries(snapshots).map(([key, value]) => <option key={key} value={key}>{value.state}{value.target_id ? ` · ${targets[value.target_id].label}` : ''}{key === 'INVALID_RECEIPT' ? ' · invalid receipt' : ''}</option>)}</select></label></section>
    </main>
    <footer><span>LineOfSight / Junction 2026 / K0 foundation</span><span>Hub run: <code>{health?.run_id ?? 'unavailable'}</code></span></footer>
  </div>;
}

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const healthResult = fetch('/health', { signal: controller.signal }).then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          return response.json();
        }).then((health) => ({ health }), (err) => ({ healthError: err.message }));
        const response = await fetch('/fixtures/snapshots.json', { signal: controller.signal });
        if (!response.ok) throw new Error(`Fixture load failed: HTTP ${response.status}`);
        const snapshots = await response.json();
        const status = await healthResult;
        if (!controller.signal.aborted) setData({ snapshots, ...status });
      } catch (err) { if (!controller.signal.aborted) setError(err.message); }
    }
    load();
    return () => controller.abort();
  }, []);
  if (error) return <main className="load-error"><h1>Unable to load fixture UI</h1><p role="alert">{error}</p><a href="/expense">Reload Expenses</a></main>;
  if (!data) return <main className="loading" role="status">Loading LineOfSight fixture UI…</main>;
  const targetId = window.location.pathname === '/json' ? 'json' : 'expenses';
  return <TargetShell key={targetId} targetId={targetId} {...data} />;
}

createRoot(document.getElementById('root')).render(<App />);
