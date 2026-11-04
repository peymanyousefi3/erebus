"""Verify portable audit inputs, source confidence, bounds and HTTP receipts."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from types import SimpleNamespace
from queue import Queue
import http.server
import json
import sys
import urllib.request
import urllib.error

main = Path(__file__).resolve().parents[1] / 'game/controllers/MainSupervisor'
sys.path.insert(0, str(main))
from AccessAudit import AccessAudit
from RobotWindowSender import RWSender
from ControllerUploader import SimpleHTTPRequestHandler

with TemporaryDirectory() as temporary:
    audit = AccessAudit(temporary)
    audit.start()
    sender = RWSender(SimpleNamespace(wwiSendText=lambda value: None), audit)
    sender.update_received_history('showMapReview', 'private arguments')
    assert audit.snapshot()[1]['total'] == 0, 'Normal supervisor actions were retained'
    for _ in range(1000):
        audit.record_command('run')
        audit.record('Referee interface', 'Opened normal preview')
    assert audit.snapshot()[0] == 0 and audit._queue.empty()
    warning = '''WARNING: Cannot read 'C:\\Erebus\\thumbnails\\missing.png', sending "404 Not Found".'''
    assert audit.report_webots_warning(json.dumps({'message': warning, 'peer':'forged-team'}))
    for bad in ('bad json', '[]', '{"message":"a download succeeded"}', 'x' * 4097):
        assert not audit.report_webots_warning(bad)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), SimpleHTTPRequestHandler)
    server.access_audit = audit
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/worlds/private.wbt?secret=hidden')
        raise AssertionError('Uploader served a forbidden file')
    except urllib.error.HTTPError as error:
        assert error.code == 403
    finally:
        try:
            urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{server.server_port}/probe', method='TRACE'))
            raise AssertionError('Unsupported request accepted')
        except urllib.error.HTTPError as error:
            assert error.code == 501
        server.shutdown()
        server.server_close()
        thread.join()
    revision, view = audit.snapshot()
    assert view['total'] == 3 and view['warnings'] == 3 and view['dropped'] == 0
    relay = view['events'][0]
    assert relay['trust'] == 'browser-relayed-unverified' and relay['peer'] == ''
    assert 'missing.png' in relay['summary'] and 'C:' not in relay['summary']
    upload = view['events'][1]
    assert upload['trust'] == 'server-received' and upload['peer'] == '127.0.0.1'
    assert '403' in upload['summary']
    public = json.dumps(view)
    assert 'private arguments' not in public and 'hidden' not in public
    audit.close()
    saved = [json.loads(line) for line in (audit.directory/'events.jsonl').read_text().splitlines()]
    assert len(saved) == 3 and saved[0]['details']['reported_warning'] == warning
    assert saved[1]['details']['status'] == '403'
    assert saved[2]['details']['status'] == '501' and saved[2]['warning']

with TemporaryDirectory() as temporary:
    audit = AccessAudit(temporary)
    audit._queue = Queue(maxsize=1)
    audit.record('Probe', 'first', warning=True)
    audit.record('Probe', 'second', warning=True)
    assert audit.snapshot()[1]['dropped'] == 1

with TemporaryDirectory() as temporary:
    audit = AccessAudit(temporary)
    audit.MAX_LOG_BYTES = 1
    audit.record('Probe', 'over-capacity', warning=True)
    audit.start()
    audit.close()
    assert 'capacity' in audit.snapshot()[1]['error']

source = (main/'AccessAudit.py').read_text()
assert not any(token in source for token in ('subprocess', 'sys.platform', 'ctypes', 'tcpdump', 'tshark'))
print('PASS: normal activity excluded without queue/revision work, real HTTP denial, unverified warning reports, UI redaction, bounded queue/log and platform-independent runtime.')
