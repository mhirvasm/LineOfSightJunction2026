"""Coffee on/off over real marker pixels and sockets; no extraction request."""

import argparse
import asyncio
from contextlib import AsyncExitStack
import json
from pathlib import Path
import socket
import sys
from uuid import uuid4

import httpx
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_hub_server import receive_until, start, stop
from scripts.verify_vision import camera_frame


async def exercise(port, browser=False, once=False):
    ws = f'ws://127.0.0.1:{port}/v1/events'
    async with AsyncExitStack() as stack:
        phone = await stack.enter_async_context(connect(ws+'?role=mobile'))
        screen = None if browser else await stack.enter_async_context(connect(ws+'?role=target&id=coffee'))
        http = await stack.enter_async_context(httpx.AsyncClient(base_url=f'http://127.0.0.1:{port}', trust_env=False))
        current = await receive_until(phone, lambda s: s['type']=='SNAPSHOT' and s['connections']['targets']['coffee'])
        run = current['run_id']
        async def event(action, **fields):
            await phone.send(json.dumps(dict(v=1,type='ACTION',run_id=run,action=action,**fields)))
        await event('START')
        stream = str(uuid4())
        await phone.send(json.dumps(dict(v=1,type='STREAM_STARTED',run_id=run,stream_id=stream,input_source='fixture_frames')))
        await receive_until(phone,lambda s:s['type']=='SNAPSHOT' and s['vision']['stream_id']==stream)
        sequence = 0
        before = current['coffee_on']
        for expected in ([not before] if once else [True, False]):
            for _ in range(5):
                sequence += 1
                response = await http.post('/v1/frames',data=dict(run_id=run,stream_id=stream,frame_seq=str(sequence),age_ms='0'),files={'image':('marker.jpg',camera_frame(((40,360,240),)),'image/jpeg')})
                assert response.status_code == 202
                await asyncio.sleep(.12)
            # unchanged fresh observations do not broadcast another snapshot.
            looked = current if current.get('can_select_coffee') else await receive_until(phone,lambda s:s['type']=='SNAPSHOT' and s.get('can_select_coffee'))
            assert looked['coffee_on'] != expected, 'Looking must not toggle'
            canceled = str(uuid4())
            await event('SELECT_COFFEE',capture_id=canceled)
            held = await receive_until(phone,lambda s:s['type']=='SNAPSHOT' and s['state']=='PREVIEW' and s['capture_id']==canceled)
            assert held['coffee_on'] != expected and held['receipt'] is None and held['text'] is None
            await event('CANCEL',capture_id=canceled)
            await receive_until(phone,lambda s:s['type']=='SNAPSHOT' and s['state']=='READY')
            capture = str(uuid4())
            await event('SELECT_COFFEE',capture_id=capture)
            held = await receive_until(phone,lambda s:s['type']=='SNAPSHOT' and s['state']=='PREVIEW' and s['capture_id']==capture)
            commit = held['preview_id']
            await event('CONFIRM',preview_id=commit,capture_id=capture)
            applied = await receive_until(screen or phone,lambda s:s['type']=='SNAPSHOT' and s.get('last_commit') and s['last_commit']['commit_id']==commit)
            assert applied['coffee_on'] == expected and all(v is None for v in applied['drafts'].values())
            if screen:
                await screen.send(json.dumps(dict(v=1,type='DISPLAYED',run_id=run,target_id='coffee',commit_id=commit)))
            await receive_until(phone,lambda s:s['type']=='SNAPSHOT' and s.get('last_commit') and s['last_commit']['commit_id']==commit and s['last_commit']['display_status']=='displayed')
            await event('CONFIRM',preview_id=commit,capture_id=capture)
            await event('CANCEL',capture_id=capture)
            after = await receive_until(phone,lambda s:s['type']=='SNAPSHOT' and s['state']=='APPLIED' and s.get('last_commit') and s['last_commit']['commit_id']==commit)
            assert after['coffee_on']==expected
            current = after
        print('PASS: Coffee look/hold/cancel/confirm, duplicate, acknowledgement and unchanged drafts over HTTP/WS.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int)
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if args.port:
        asyncio.run(exercise(args.port, args.browser, args.once))
    else:
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0)); port=listener.getsockname()[1]
        (ROOT/'tmp').mkdir(exist_ok=True)
        with (ROOT/'tmp/coffee-server.log').open('w') as log:
            process, _ = start(port,log)
            try: asyncio.run(exercise(port))
            finally: stop(process)
