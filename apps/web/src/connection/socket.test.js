import { test } from 'node:test';
import assert from 'node:assert/strict';
import { connectHub } from './socket.js';

function harness() {
  const sockets = [], timers = [], updates = [], statuses = [], errors = [];
  class Socket {
    constructor(url) { this.url = url; this.readyState = 1; this.sent = []; sockets.push(this); }
    send(value) { this.sent.push(JSON.parse(value)); }
    close() { this.readyState = 3; this.onclose?.({ code: 1000 }); }
    receive(message) { this.onmessage({ data: JSON.stringify(message) }); }
  }
  const connection = connectHub({ role: 'target', targetId: 'json', WebSocketClass: Socket,
    location: { href: 'http://demo.local/json', protocol: 'http:' },
    onSnapshot: (value) => updates.push(value), onStatus: (value) => statuses.push(value), onError: (value) => errors.push(value),
    schedule: (callback) => { timers.push(callback); return timers.length; },
    cancel: (id) => { if (id) timers[id - 1] = null; },
  });
  return { connection, sockets, timers, updates, statuses, errors };
}

test('new-run snapshots replace state and sends use the current run', () => {
  const h = harness();
  assert.match(h.sockets[0].url, /role=target&id=json/);
  assert.equal(h.connection.send({ type: 'RESET' }), false);
  h.sockets[0].receive({ v: 1, type: 'SNAPSHOT', run_id: 'first', drafts: { json: 'old' } });
  h.sockets[0].receive({ v: 1, type: 'SNAPSHOT', run_id: 'second', drafts: { json: null } });
  assert.equal(h.updates.at(-1).drafts.json, null);
  assert.equal(h.connection.send({ type: 'RESET', run_id: 'stale' }), true);
  assert.equal(h.sockets[0].sent[0].run_id, 'second');
  h.connection.dispose();
});

test('disconnect clears stale state; reconnect never replays sent actions', () => {
  const h = harness();
  h.sockets[0].receive({ v: 1, type: 'SNAPSHOT', run_id: 'first' });
  h.connection.send({ type: 'RESET' });
  h.sockets[0].close();
  assert.equal(h.updates.at(-1), null);
  assert.equal(h.connection.send({ type: 'RESET' }), false);
  h.timers[0]();
  assert.equal(h.sockets.length, 2);
  assert.deepEqual(h.sockets[1].sent, []);
  h.sockets[0].receive({ v: 1, type: 'SNAPSHOT', run_id: 'obsolete' });
  assert.equal(h.updates.at(-1), null);
  h.connection.dispose();
});

test('duplicate connection is visible and does not start a reconnect loop', () => {
  const h = harness();
  h.sockets[0].receive({ v: 1, type: 'ERROR', error: 'connection_rejected', message: 'Already active' });
  h.sockets[0].close();
  assert.equal(h.statuses.at(-1), 'Connection rejected');
  assert.equal(h.errors.at(-1), 'Already active');
  assert.equal(h.timers.length, 0);
  h.connection.dispose();
});

test('cleanup cancels reconnect timers and ignores obsolete callbacks', () => {
  const h = harness();
  h.sockets[0].close();
  h.connection.dispose();
  assert.equal(h.timers[0], null);
  const length = h.updates.length;
  h.sockets[0].receive({ v: 1, type: 'SNAPSHOT', run_id: 'late' });
  assert.equal(h.updates.length, length);
});
