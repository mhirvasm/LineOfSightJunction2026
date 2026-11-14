import { useEffect, useRef, useState } from 'react';
import { connectHub } from './socket.js';

export function useHub(role, targetId) {
  const [snapshot, setSnapshot] = useState(null);
  const [status, setStatus] = useState('Connecting');
  const [error, setError] = useState(null);
  const connection = useRef(null);
  useEffect(() => {
    setSnapshot(null);
    setError(null);
    const current = connectHub({ role, targetId, onSnapshot: setSnapshot, onStatus: setStatus, onError: setError });
    connection.current = current;
    return () => {
      connection.current = null;
      current.dispose();
    };
  }, [role, targetId]);
  return { snapshot, status, error,
    readSnapshot: () => connection.current?.getSnapshot() ?? null,
    send: (event) => connection.current?.send(event) ?? false };
}
