"""Full receipt flow over real HTTP/WS with synthetic JPEGs and explicit fixture reading."""

import asyncio
import json
import os
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


async def exercise(port, live=False, text_only=False):
    origin = f'http://127.0.0.1:{port}'
    ws = f'ws://127.0.0.1:{port}/v1/events'
    async with connect(ws+'?role=mobile') as mobile, connect(ws+'?role=target&id=expenses') as expenses, connect(ws+'?role=target&id=json') as target_json, connect(ws+'?role=target&id=text') as target_text, httpx.AsyncClient(base_url=origin, trust_env=False) as http:
        snapshot = await receive_until(mobile, lambda s: s['type']=='SNAPSHOT')
        run = snapshot['run_id']
        async def event(action, **fields):
            await mobile.send(json.dumps(dict(v=1, type='ACTION', run_id=run, action=action, **fields)))
        await event('START')
        stream = str(uuid4())
        await mobile.send(json.dumps(dict(v=1, type='STREAM_STARTED', run_id=run, stream_id=stream, input_source='fixture_frames')))
        await receive_until(mobile, lambda s: s['type']=='SNAPSHOT' and s['vision']['stream_id']==stream)
        seq = 0
        destinations = [('text',30,target_text), ('json',20,target_json)] if text_only else [('expenses',10,expenses), ('json',20,target_json), ('text',30,target_text)]
        for target, marker, screen in destinations:
            capture = str(uuid4())
            data = dict(run_id=run, capture_id=capture, age_ms='0')
            if live:
                from scripts.verify_live_receipts import receipt_jpeg
                if text_only:
                    from scripts.verify_live_text import text_jpeg, NOTE
                    image = text_jpeg(NOTE)
                else:
                    image = receipt_jpeg("24.80")
            else:
                image = camera_frame()
            response = await http.post('/v1/captures', data=data, files={'image':('receipt.jpg', image, 'image/jpeg')})
            assert response.status_code == 202, response.text
            duplicate = await http.post('/v1/captures', data=data, files={'image':('receipt.jpg', image, 'image/jpeg')})
            assert duplicate.status_code == 202
            await receive_until(mobile, lambda s: s['type']=='SNAPSHOT' and s['capture_id']==capture and s['state'] in ('HOLDING','PREVIEW'), timeout=30)
            for _ in range(5):
                seq += 1
                response = await http.post('/v1/frames', data=dict(run_id=run, stream_id=stream, age_ms='0', frame_seq=str(seq)), files={'image':('frame.jpg', camera_frame(((marker,360,240),)), 'image/jpeg')})
                assert response.status_code == 202
                await asyncio.sleep(.12)
            ready = await receive_until(mobile, lambda s: s['type']=='SNAPSHOT' and s['state']=='PREVIEW' and s['target_id']==target)
            preview = ready['preview_id']
            await event('CONFIRM', preview_id=preview, capture_id=capture)
            applied = await receive_until(screen, lambda s: s['type']=='SNAPSHOT' and s.get('last_commit',{} ) and s['last_commit']['commit_id']==preview)
            if text_only or target == 'text':
                assert applied['drafts'][target] == {'text': ready['text']}
                if text_only: assert ready['receipt'] is None and '14:30' in ready['text']
            else:
                assert applied['drafts'][target]['total_minor']==2480
            await screen.send(json.dumps(dict(v=1,type='DISPLAYED',run_id=run,target_id=target,commit_id=preview)))
            await receive_until(mobile, lambda s: s['type']=='SNAPSHOT' and s.get('last_commit') and s['last_commit']['display_status']=='displayed')
            await event('CONFIRM', preview_id=preview)
            await event('CANCEL', capture_id=capture)
            after = await receive_until(mobile, lambda s: s['type']=='SNAPSHOT' and s['state']=='APPLIED')
            assert after['drafts'][target] == applied['drafts'][target]
        canceled = str(uuid4())
        await event('CANCEL', capture_id=canceled)
        await receive_until(mobile, lambda s: s['type']=='SNAPSHOT')
        response = await http.post('/v1/captures', data=dict(run_id=run,capture_id=canceled,age_ms='0'),files={'image':('receipt.jpg',image,'image/jpeg')})
        assert response.status_code==409
        await event('UNDO')
        undone = await receive_until(mobile, lambda s: s['type']=='SNAPSHOT' and s['state']=='READY')
        assert undone['drafts'][destinations[-1][0]] is None
        assert undone['drafts'][destinations[0][0]] is not None


if __name__=='__main__':
    live = '--live' in sys.argv
    text_only = '--text' in sys.argv
    os.environ['LOS_FIXTURE_CONTENT'] = 'text' if text_only else 'receipt'
    if live:
        import scripts.run_hub
    os.environ['LOS_EXTRACTION_MODE'] = 'live' if live else 'fixture'
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0)); port=listener.getsockname()[1]
    (ROOT/'tmp').mkdir(exist_ok=True)
    with (ROOT/'tmp/workflow-server.log').open('w') as log:
        process,_=start(port,log)
        try: asyncio.run(exercise(port, live, text_only))
        finally: stop(process)
    print(('LIVE provider' if live else 'FIXTURE extraction') + ': ' + ('text-only' if text_only else 'receipt and transcription') + ' capture, all compatible destinations, acknowledgements, duplicate send, release after send, cancel-before-upload and Undo over HTTP/WS.')
