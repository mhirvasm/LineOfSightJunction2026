export function connectHub({ role, targetId, onSnapshot, onStatus, onError, WebSocketClass = WebSocket, location = window.location, schedule = setTimeout, cancel = clearTimeout }) {
  let socket;
  let timer;
  let disposed = false;
  let snapshot = null;
  let rejected = false;
  function open() {
    if (disposed) return;
    onStatus('Connecting');
    const url = new URL('/v1/events', location.href);
    url.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    url.searchParams.set('role', role);
    if (targetId) url.searchParams.set('id', targetId);
    const current = new WebSocketClass(url.href);
    socket = current;
    current.onmessage = ({ data }) => {
      if (disposed || current !== socket) return;
      let event;
      try { event = JSON.parse(data); } catch { return; }
      if (event.v !== 1) return;
      if (event.type === 'SNAPSHOT') {
        snapshot = event;
        onSnapshot(event);
        onError(null);
        onStatus('Connected');
      } else if (event.type === 'ERROR') {
        if (event.error === 'connection_rejected') {
          rejected = true;
          snapshot = null;
          onSnapshot(null);
          onStatus('Connection rejected');
        }
        onError(event.message);
      }
    };
    current.onerror = () => {
      if (!disposed && current === socket) onError('Unable to connect to the hub. Check its terminal and network address.');
    };
    current.onclose = (event) => {
      if (disposed || current !== socket) return;
      snapshot = null;
      onSnapshot(null);
      if (rejected || event.code === 4409 || event.code === 4400) {
        onStatus('Connection rejected');
        return;
      }
      onStatus('Disconnected');
      timer = schedule(open, 1500);
    };
  }
  open();
  return {
    send(event) {
      if (disposed || rejected || !snapshot || socket.readyState !== 1) return false;
      socket.send(JSON.stringify({ ...event, v: 1, run_id: snapshot.run_id }));
      return true;
    },
    dispose() {
      disposed = true;
      cancel(timer);
      snapshot = null;
      socket.close();
    },
  };
}
