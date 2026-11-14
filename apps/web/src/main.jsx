import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import targets from '../../../contracts/targets.json';
import { useHub } from './connection/useHub.js';
import { PhotoTest, VisionStatus } from './phone/PhotoTest.jsx';
import { CoffeeMachine } from './CoffeeMachine.jsx';
import './styles.css';

const money = (record) => record?.total_minor == null ? 'Unreadable' :
  new Intl.NumberFormat('en-IE', { style: 'currency', currency: record.currency }).format(record.total_minor / 100);

function Header({ mode = "fixture", badge }) {
  return <header className="topbar"><a className="brand" href="/expense"><span className="brand-mark" aria-hidden="true">L<span>•</span></span>LineOfSight</a><nav aria-label="Pages">{[...Object.values(targets), { route: '/operator', label: 'Operator' }, { route: '/fixture-mobile', label: 'Test phone' }].map((item) => <a key={item.route} href={item.route} aria-current={window.location.pathname === item.route ? 'page' : undefined}>{item.label}</a>)}</nav><span className="mode-badge">{badge ?? `${mode.toUpperCase()} CAPTURE`}</span></header>;
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
    ['Phone / test controller', current?.mobile], ['Expenses screen', current?.targets.expenses], ['JSON screen', current?.targets.json], ['Text screen', current?.targets.text], ['Coffee screen', current?.targets.coffee],
  ].map(([label, connected]) => <li key={label}><span>{label}</span><strong>{current ? (connected ? 'Connected' : 'Not connected') : 'Unknown'}</strong></li>)}</ul><p>All connected pages should show the same hub run number below.</p></section>;
}

function TextResult({ record, preview = false }) {
  const corrected = record.text_status === 'ready';
  return <div className="text-result">
    <h3>{corrected ? 'AI-corrected text' : 'Original transcription'}</h3>
    {record.text_status === 'unavailable' && <p className="muted">Cleanup unavailable. Showing the original transcription.</p>}
    <div className={preview ? 'text-preview' : 'pasted-text'} aria-label={preview ? 'Text preview' : 'Pasted text'} dir="auto">{record.text}</div>
    {record.summary && <section className="text-summary"><h3>Short summary</h3><p dir="auto">{record.summary}</p></section>}
    {corrected && record.raw_text && <section className="original-text"><h3>Original transcription</h3><div dir="auto">{record.raw_text}</div></section>}
  </div>;
}

function Receipt({ record, targetId }) {
  if (!record) return <div className="empty"><span className="empty-icon" aria-hidden="true">—</span><p>{targetId === 'text' ? 'No pasted text yet' : 'No applied draft'}</p><small>Hold, aim here, then drag right to paste.</small></div>;
  if (targetId === 'text') return <TextResult record={record} />;
  if (targetId === 'json') return <pre>{JSON.stringify(record, null, 2)}</pre>;
  const fields = [
    ['Merchant', record.merchant ?? 'Needs review'], ['Date', record.date ?? 'Needs review'],
    ['Total', money(record)], ['Currency', record.currency],
    ['Tax', record.tax_minor == null ? 'Not provided (optional)' : money({ ...record, total_minor: record.tax_minor })],
  ];
  return <dl className="receipt-fields">{fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function CapturePreview({ snapshot, targetId }) {
  if (snapshot?.target_id !== targetId || !snapshot?.can_confirm) return <p className="muted">{snapshot?.text || snapshot?.receipt ? 'Aim here while holding. A compatible capture is required.' : 'No active capture.'}</p>;
  if (targetId === 'text' || !snapshot.receipt) return <TextResult record={snapshot} preview />;
  return <><div className="preview-total">{money(snapshot.receipt)}</div><p className="preview-merchant">{snapshot.receipt.merchant} · {snapshot.receipt.date}</p></>;
}

function TargetShell({ targetId, snapshot, status, error, example = false, children }) {
  const target = targets[targetId];
  useEffect(() => { document.title = `${target.label} · LineOfSight`; }, [target.label]);
  return <div className="app-shell"><Header mode={snapshot?.source_mode} /><main>
    <div className="page-heading"><div><p className="eyebrow">REGISTERED DESTINATION / {target.marker_id}</p><h1>{target.label}</h1><p className="subtitle">Look here. Review your capture. Drag right to paste.</p></div><Status status={status} error={error} /></div>
    <div className="fixture-notice"><strong>{example ? 'Predetermined layout example' : 'Hold, aim, drag right'}</strong><span>{example ? 'This page shows local sample data and has no hub socket.' : 'Hold to grab text or a receipt. Face this marker, review the preview, then drag right to paste. Release to cancel.'}</span></div>
    <div className="workspace">
      <section className="marker-panel" aria-label={`${target.label} target marker`}><div className="panel-top"><span>YOUR TARGET</span><span>MARKER {target.marker_id}</span></div><div className="marker-tile"><img src={target.marker_asset} alt={`ArUco DICT_4X4_50 marker ${target.marker_id}`} width="600" height="600" /></div><h2>{target.label}</h2><p>Keep this marker visible to the glasses.</p><span className="dictionary">DICT_4X4_50 · ID {target.marker_id}</span></section>
      <div className="data-column">
        <section className="card preview-card"><div className="card-title"><h2>Capture preview</h2><span className="state-chip">{snapshot?.state ?? 'WAITING'}</span></div><p className="feedback">{snapshot?.feedback ?? 'Waiting for a current hub snapshot.'}</p><CapturePreview snapshot={snapshot} targetId={targetId} /><div className="preview-footer">{example ? "Sample only" : "Only a deliberate confirmation updates the draft"}</div></section>
        <section className="card applied-card"><div className="card-title"><h2>{targetId === 'text' ? 'Pasted text' : targetId === 'json' ? 'Applied JSON' : 'Applied expense draft'}</h2><span className="read-only">READ ONLY</span></div><Receipt record={snapshot?.drafts[targetId]} targetId={targetId} /></section>
      </div>
    </div>
    {example ? children : <><VisionStatus snapshot={snapshot} /><Connections snapshot={snapshot} /><p className="example-link"><a href={`${target.route}?fixture=PREVIEW_${targetId}`}>Open the separate layout examples</a></p></>}
  </main><Footer runId={snapshot?.run_id} /></div>;
}

function ConnectedTarget({ targetId }) {
  const hub = useHub('target', targetId);
  useEffect(() => {
    const acknowledge = () => {
      const snapshot = hub.readSnapshot();
      const commit = snapshot?.last_commit;
      if (document.visibilityState === 'visible' && commit?.target_id === targetId && commit.display_status !== 'displayed') {
        hub.send({ type: 'DISPLAYED', target_id: targetId, commit_id: commit.commit_id });
      }
    };
    const frame = requestAnimationFrame(acknowledge);
    document.addEventListener('visibilitychange', acknowledge);
    return () => { cancelAnimationFrame(frame); document.removeEventListener('visibilitychange', acknowledge); };
  }, [hub.snapshot, targetId]);
  if (targetId === 'coffee') return <div className="app-shell"><Header badge="SIMULATED APPLIANCE" /><main>
    <div className="page-heading"><div><p className="eyebrow">REGISTERED APPLIANCE / 40</p><h1>Coffee machine</h1><p className="subtitle">Look. Hold. Swipe right. Your next cup starts here.</p></div><Status status={hub.status} error={hub.error} /></div>
    <div className="fixture-notice"><strong>Simulated coffee machine</strong><span>Hold while aiming here, then swipe right to turn it on or off. Release to cancel.</span></div>
    <div className="workspace coffee-workspace">
      <section className="marker-panel" aria-label="Coffee target marker"><div className="panel-top"><span>YOUR TARGET</span><span>MARKER 40</span></div><div className="marker-tile"><img src={targets.coffee.marker_asset} alt="ArUco DICT_4X4_50 marker 40" width="600" height="600" /></div><h2>Coffee</h2><p>Looking identifies it. Your swipe controls it.</p></section>
      <section className="card coffee-card"><div className="card-title"><h2>Espresso station</h2><span className={hub.snapshot?.coffee_on ? 'coffee-power on' : 'coffee-power'}>{hub.snapshot?.coffee_on ? 'ON' : 'OFF'}</span></div><CoffeeMachine on={Boolean(hub.snapshot?.coffee_on)} />
      <h2 className="coffee-state" role="status">{hub.snapshot?.coffee_on ? 'Brewing your coffee' : 'Ready when you are'}</h2>
      <p className="coffee-hint">{hub.snapshot?.coffee_on ? 'Hold and swipe right again to stop.' : 'Hold and swipe right to start.'}</p>
      <p className="feedback">{hub.snapshot?.target_id === 'coffee' ? hub.snapshot.feedback : 'Aim the phone or glasses at marker 40.'}</p></section>
    </div><Connections snapshot={hub.snapshot} /><VisionStatus snapshot={hub.snapshot} />
  </main><Footer runId={hub.snapshot?.run_id} /></div>;
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
  return <div className="app-shell"><Header mode={hub.snapshot?.source_mode} /><main>
    <div className="page-heading"><div><p className="eyebrow">PHONE / SCREEN MARKER TEST</p><h1>{title}</h1></div><Status status={hub.status} error={hub.error} /></div>
    <div className="fixture-notice"><strong>{operator ? 'Operator controls' : 'PHONE CAMERA FALLBACK · no glasses connected'}</strong><span>{operator ? 'Reset clears the entire shared run and all drafts.' : 'This browser occupies the phone connection. Its optional photo test uses phone images, not glasses input. Close it before connecting a native app.'}</span></div>
    <Connections snapshot={hub.snapshot} />
    {!operator && <PhotoTest hub={hub} />}
    <VisionStatus snapshot={hub.snapshot} />
    <section className="card test-controls"><h2>{operator ? 'Test the shared connection' : 'What this proves'}</h2><p>{operator ? 'Open Expenses, JSON, Text, and Test phone. Check that all four appear above. Press Reset, then check that every page receives the same new hub run number.' : 'The server can receive a phone photo and recognize its registered screen marker. This does not prove glasses camera access, receipt reading, or Neural Band input.'}</p>{operator && <button className="primary-button" disabled={hub.status !== 'Connected' || Boolean(pending)} onClick={reset}>{pending ? 'Resetting…' : 'Reset demo run'}</button>}<p>Current state: <strong>{hub.snapshot?.state ?? 'Waiting'}</strong></p><p>{hub.snapshot?.feedback}</p></section>
  </main><Footer runId={hub.snapshot?.run_id} /></div>;
}

function App() {
  const path = window.location.pathname;
  if (path === '/operator') return <TestPage operator />;
  if (path === '/fixture-mobile') return <TestPage operator={false} />;
  if (path === '/coffee') return <ConnectedTarget targetId="coffee" />;
  const targetId = path === '/text' ? 'text' : path === '/json' ? 'json' : 'expenses';
  return new URLSearchParams(window.location.search).has('fixture') ? <FixtureExamples targetId={targetId} /> : <ConnectedTarget targetId={targetId} />;
}

createRoot(document.getElementById('root')).render(<App />);
