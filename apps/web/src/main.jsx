import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import targets from '../../../contracts/targets.json';
import { useHub } from './connection/useHub.js';
import { PhotoTest, VisionStatus } from './phone/PhotoTest.jsx';
import './styles.css';

const money = (record) => record?.total_minor == null ? 'Unreadable' :
  new Intl.NumberFormat('en-IE', { style: 'currency', currency: record.currency }).format(record.total_minor / 100);

function Header() {
  return <header className="topbar"><a className="brand" href="/expense"><span className="brand-mark" aria-hidden="true">L<span>•</span></span>LineOfSight</a><nav aria-label="Pages">{[...Object.values(targets), { route: '/operator', label: 'Operator' }, { route: '/fixture-mobile', label: 'Test phone' }].map((item) => <a key={item.route} href={item.route} aria-current={window.location.pathname === item.route ? 'page' : undefined}>{item.label}</a>)}</nav><span className="mode-badge">FIXTURE MODE</span></header>;
}

function Footer({ runId }) {
  return <footer><span>LineOfSight / Junction 2026 / shared hub and marker test</span><span>Hub run: <code>{runId ?? 'waiting for connection'}</code></span></footer>;
}

function Status({ status, error }) {
  return <div className="hub-status" role="status"><span className={status === 'Connected' ? 'status-dot online' : 'status-dot'} />{status}<small>{error ?? (status === 'Connected' ? 'Receiving shared server updates' : 'No current server snapshot')}</small></div>;
}

function Connections({ snapshot }) {
  const current = snapshot?.connections;
  return <section className="connection-panel" aria-label="Connected devices"><h2>Shared hub connections</h2><ul>{[
    ['Phone / test controller', current?.mobile], ['Expenses screen', current?.targets.expenses], ['JSON screen', current?.targets.json],
  ].map(([label, connected]) => <li key={label}><span>{label}</span><strong>{current ? (connected ? 'Connected' : 'Not connected') : 'Unknown'}</strong></li>)}</ul><p>All connected pages should show the same hub run number below.</p></section>;
}

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

function TargetShell({ targetId, snapshot, status, error, example = false, children }) {
  const target = targets[targetId];
  const preview = snapshot?.target_id === targetId ? snapshot.receipt : null;
  useEffect(() => { document.title = `${target.label} · LineOfSight`; }, [target.label]);
  return <div className="app-shell"><Header /><main>
    <div className="page-heading"><div><p className="eyebrow">REGISTERED DESTINATION / {target.marker_id}</p><h1>{target.label}</h1><p className="subtitle">Look here. Review the receipt. Confirm deliberately.</p></div><Status status={status} error={error} /></div>
    <div className="fixture-notice"><strong>{example ? 'Predetermined layout example' : 'Shared marker test'}</strong><span>{example ? 'This page shows local sample data and has no hub socket.' : 'This page receives shared updates and phone-frame marker results. Glasses capture, receipt reading, and transfers are not connected yet.'}</span></div>
    <div className="workspace">
      <section className="marker-panel" aria-label={`${target.label} target marker`}><div className="panel-top"><span>YOUR TARGET</span><span>MARKER {target.marker_id}</span></div><div className="marker-tile"><img src={target.marker_asset} alt={`ArUco DICT_4X4_50 marker ${target.marker_id}`} width="600" height="600" /></div><h2>{target.label}</h2><p>Keep this marker visible to the glasses.</p><span className="dictionary">DICT_4X4_50 · ID {target.marker_id}</span></section>
      <div className="data-column">
        <section className="card preview-card"><div className="card-title"><h2>Receipt preview</h2><span className="state-chip">{snapshot?.state ?? 'WAITING'}</span></div><p className="feedback">{snapshot?.feedback ?? 'Waiting for a current hub snapshot.'}</p>{preview ? <><div className="preview-total">{money(preview)}</div><p className="preview-merchant">{preview.merchant ?? 'Merchant needs review'} · {preview.date ?? 'Date needs review'}</p></> : <p className="muted">{snapshot?.receipt ? 'This receipt is directed to another destination.' : 'No active receipt.'}</p>}<div className="preview-footer">{example ? 'Sample only' : 'B1 connection milestone'} · no confirmation action is connected</div></section>
        <section className="card applied-card"><div className="card-title"><h2>Applied {targetId === 'json' ? 'JSON' : 'expense draft'}</h2><span className="read-only">READ ONLY</span></div><Receipt record={snapshot?.drafts[targetId]} targetId={targetId} /></section>
      </div>
    </div>
    {example ? children : <><VisionStatus snapshot={snapshot} /><Connections snapshot={snapshot} /><p className="example-link"><a href={`${target.route}?fixture=PREVIEW_${targetId}`}>Open the separate layout examples</a></p></>}
  </main><Footer runId={snapshot?.run_id} /></div>;
}

function ConnectedTarget({ targetId }) {
  const hub = useHub('target', targetId);
  return <TargetShell targetId={targetId} {...hub} />;
}

function FixtureExamples({ targetId }) {
  const initial = new URLSearchParams(window.location.search).get('fixture');
  const [fixtureId, setFixtureId] = useState(initial);
  const [snapshots, setSnapshots] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/fixtures/snapshots.json', { signal: controller.signal }).then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }).then((value) => { if (!controller.signal.aborted) setSnapshots(value); })
      .catch((failure) => { if (!controller.signal.aborted) setError(failure.message); });
    return () => controller.abort();
  }, []);
  if (error) return <main role="alert">Fixture load failed: {error}</main>;
  if (!snapshots) return <main role="status">Loading layout examples…</main>;
  const selected = fixtureId in snapshots ? fixtureId : `PREVIEW_${targetId}`;
  return <TargetShell targetId={targetId} snapshot={snapshots[selected]} status="Local layout example" example>
    <section className="fixture-controls"><div><h2>UI fixture examples</h2><p>Changes the local example only. Does not change hub memory.</p><a href={targets[targetId].route}>Return to the connected screen</a></div><label>Example state<select value={selected} onChange={(event) => setFixtureId(event.target.value)}>{Object.entries(snapshots).map(([key, value]) => <option key={key} value={key}>{value.state}{value.target_id ? ` · ${targets[value.target_id].label}` : ''}{key === 'INVALID_RECEIPT' ? ' · invalid receipt' : ''}</option>)}</select></label></section>
  </TargetShell>;
}

function TestPage({ operator }) {
  const hub = useHub(operator ? 'operator' : 'mobile');
  const [pendingRun, setPendingRun] = useState(null);
  const pending = pendingRun && pendingRun === hub.snapshot?.run_id && hub.status === 'Connected';
  const title = operator ? 'Connection test operator' : 'Test phone connection';
  useEffect(() => { document.title = `${title} · LineOfSight`; }, [title]);
  function reset() {
    if (hub.send({ type: 'RESET' })) setPendingRun(hub.snapshot.run_id);
  }
  return <div className="app-shell"><Header /><main>
    <div className="page-heading"><div><p className="eyebrow">PHONE / SCREEN MARKER TEST</p><h1>{title}</h1></div><Status status={hub.status} error={hub.error} /></div>
    <div className="fixture-notice"><strong>{operator ? 'Operator controls' : 'PHONE CAMERA FALLBACK · no glasses connected'}</strong><span>{operator ? 'Reset clears the entire shared run and both drafts.' : 'This browser occupies the phone connection. Its optional photo test uses phone images, not glasses input. Close it before connecting a native app.'}</span></div>
    <Connections snapshot={hub.snapshot} />
    {!operator && <PhotoTest hub={hub} />}
    <VisionStatus snapshot={hub.snapshot} />
    <section className="card test-controls"><h2>{operator ? 'Test the shared connection' : 'What this proves'}</h2><p>{operator ? 'Open Expenses, JSON, and Test phone. Check that all three appear above. Press Reset, then check that every page receives the same new hub run number.' : 'The server can receive a phone photo and recognize its registered screen marker. This does not prove glasses camera access, receipt reading, or Neural Band input.'}</p>{operator && <button className="primary-button" disabled={hub.status !== 'Connected' || Boolean(pending)} onClick={reset}>{pending ? 'Resetting…' : 'Reset demo run'}</button>}<p>Current state: <strong>{hub.snapshot?.state ?? 'Waiting'}</strong></p><p>{hub.snapshot?.feedback}</p></section>
  </main><Footer runId={hub.snapshot?.run_id} /></div>;
}

function App() {
  const path = window.location.pathname;
  if (path === '/operator') return <TestPage operator />;
  if (path === '/fixture-mobile') return <TestPage operator={false} />;
  const targetId = path === '/json' ? 'json' : 'expenses';
  return new URLSearchParams(window.location.search).has('fixture') ? <FixtureExamples targetId={targetId} /> : <ConnectedTarget targetId={targetId} />;
}

createRoot(document.getElementById('root')).render(<App />);
