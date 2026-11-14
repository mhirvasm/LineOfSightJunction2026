import React, { useEffect, useRef, useState } from 'react';

function streamId() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  const hex = [...bytes].map((value) => value.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

async function jpegFromPhoto(file) {
  if (file.size > 20_000_000) throw new Error('Choose a photo smaller than 20 MB.');
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
  const deliveredAt = performance.now();
  try {
    const scale = Math.min(1, 1280 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', .82));
    if (!blob || blob.size > 2_000_000) throw new Error('Photo could not be converted to a JPEG under 2 MB.');
    return { blob, deliveredAt };
  } finally { bitmap.close(); }
}

export function VisionStatus({ snapshot }) {
  const vision = snapshot?.vision;
  const name = (value) => value === 'expenses' ? 'Expenses' : value === 'json' ? 'JSON' : 'None';
  return <section className="card vision-panel" aria-label="Marker recognition"><h2>Marker recognition</h2>
    <dl className="receipt-fields"><div><dt>Last image recognized</dt><dd>{name(vision?.detected_target_id)}</dd></div><div><dt>Fresh candidate</dt><dd>{name(vision?.candidate_id)}</dd></div><div><dt>Stable target</dt><dd>{name(vision?.locked_target_id)}</dd></div></dl>
    <p role="status">{vision?.message ?? 'Waiting for the camera-test connection.'}</p>
    <small>A single photo checks recognition. Continuous fresh frames are required to keep a target selected.</small>
  </section>;
}

export function PhotoTest({ hub }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('Aim at one screen marker and take a photo.');
  const [preview, setPreview] = useState(null);
  const stream = useRef(null);
  const request = useRef(null);
  const previewUrl = useRef(null);
  const epoch = useRef(0);

  function clear() {
    epoch.current += 1;
    request.current?.abort();
    request.current = null;
    stream.current = null;
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null;
    setPreview(null);
    setBusy(false);
  }
  useEffect(() => {
    clear();
    setMessage('Take a new photo when the phone connection is ready.');
    return () => {
      epoch.current += 1;
      request.current?.abort();
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    };
  }, [hub.snapshot?.run_id, hub.status]);

  async function sendPhoto(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || busy) return;
    const initial = hub.readSnapshot();
    if (!initial) { setMessage('Connect to the hub first.'); return; }
    const currentEpoch = epoch.current;
    const checkCurrent = () => {
      if (epoch.current !== currentEpoch || hub.readSnapshot()?.run_id !== initial.run_id) throw new Error('The run or connection changed. Take a new photo.');
    };
    setBusy(true);
    setMessage('Preparing the phone photo…');
    try {
      if (!stream.current || stream.current.runId !== initial.run_id || hub.readSnapshot()?.vision?.stream_id !== stream.current.id) {
        const id = streamId();
        if (initial.state === 'STOPPED' && !hub.send({ type: 'ACTION', action: 'START' })) throw new Error('Phone is disconnected.');
        if (!hub.send({ type: 'STREAM_STARTED', stream_id: id, input_source: 'phone_photo' })) throw new Error('Phone is disconnected.');
        stream.current = { runId: initial.run_id, id, sequence: 0 };
        const deadline = performance.now() + 3000;
        while (hub.readSnapshot()?.vision?.stream_id !== id || hub.readSnapshot()?.state === 'STOPPED') {
          checkCurrent();
          if (performance.now() > deadline) throw new Error('The hub did not acknowledge the camera stream. Try again after reconnecting.');
          await new Promise((resolve) => setTimeout(resolve, 30));
        }
      }
      checkCurrent();
      const { blob, deliveredAt } = await jpegFromPhoto(file);
      checkCurrent();
      const age = Math.floor(performance.now() - deliveredAt);
      if (age > 300) throw new Error('Photo conversion took too long. Try a smaller photo.');
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
      previewUrl.current = URL.createObjectURL(blob);
      setPreview(previewUrl.current);
      const form = new FormData();
      const sequence = ++stream.current.sequence;
      form.set('run_id', initial.run_id);
      form.set('stream_id', stream.current.id);
      form.set('frame_seq', String(sequence));
      form.set('age_ms', String(age));
      form.set('image', blob, 'phone-frame.jpg');
      const controller = new AbortController();
      request.current = controller;
      const timeout = setTimeout(() => controller.abort(), 5000);
      let response;
      try { response = await fetch('/v1/frames', { method: 'POST', body: form, signal: controller.signal }); }
      finally { clearTimeout(timeout); }
      const result = await response.json();
      checkCurrent();
      if (!response.ok) throw new Error(result.detail ?? `Upload failed: HTTP ${response.status}`);
      setMessage(`Photo ${sequence} accepted for marker analysis. Read the result below. This photo is not a live camera stream.`);
    } catch (failure) {
      if (epoch.current === currentEpoch) setMessage(failure.name === 'AbortError' ? 'Upload stopped or timed out. Take a new photo.' : failure.message);
    } finally {
      if (epoch.current === currentEpoch) { request.current = null; setBusy(false); }
    }
  }

  function stop() {
    clear();
    hub.send({ type: 'ACTION', action: 'STOP' });
    setMessage('Camera test stopped. Applied drafts are unchanged.');
  }

  return <section className="card photo-test"><h2>Phone camera / photo test</h2>
    <p>Keep Expenses and JSON visible on the laptop. Aim at only one large marker, with the whole square near the centre. This tests the phone camera/photo picker, not the glasses.</p>
    <label className="photo-label">Take or choose a photo<input type="file" accept="image/*" capture="environment" onChange={sendPhoto} disabled={hub.status !== 'Connected' || busy} /></label>
    <button className="secondary-button" onClick={stop} disabled={hub.status !== 'Connected'}>Stop camera test</button>
    <p role="status">{message}</p>
    {preview && <div className="photo-preview"><img src={preview} alt="Normalized JPEG sent for marker detection" /><span className="central-region" aria-hidden="true" /></div>}
    <small>The outlined central half is the selection area. A photo may have been taken earlier; the local upload age does not prove sensor freshness. No photo is replayed automatically.</small>
  </section>;
}
