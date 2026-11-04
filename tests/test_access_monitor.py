"""Access evidence must be accurate, bounded and absent from public UI payloads."""
from pathlib import Path
import hashlib
import io
import json
import stat
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'game/controllers/MainSupervisor'))
from AccessMonitor import AccessMonitor, resource_kind, server_port


def packet(**fields):
    return {key: value.hex() if isinstance(value, bytes) else str(value) for key, value in fields.items()}


def request(monitor, number, uri, source='172.17.0.2'):
    monitor._http(packet(**{'frame.number': number, 'frame.time_epoch': '1700000000',
                             'tcp.stream': '4', 'ip.src': source, 'tcp.srcport': '45000',
                             'http.request.method': 'GET', 'http.request.uri': uri}))


def response(monitor, request_number, body, length=None, status=200):
    monitor._http(packet(**{'frame.number': str(int(request_number) + 1),
                             'frame.time_epoch': '1700000001', 'tcp.stream': '4',
                             'http.response.code': status, 'http.request_in': request_number,
                             'http.content_length': len(body) if length is None else length,
                             'http.file_data': body}))


assert server_port('/tmp/webots/organizer/1255/') == 1255
assert server_port('C:\\Temp\\webots-1234\\') == 1234
for invalid in ('', '/tmp/webots/user/', '/tmp/webots/user/99999/'):
    try:
        server_port(invalid)
        raise AssertionError('Invalid server port accepted')
    except ValueError:
        pass
assert resource_kind('/robot_windows/MainSupervisorWindow/MainSupervisorWindow.js') is None
assert resource_kind('/robot_windows/MainSupervisorWindow/MapReview.html') is None
assert resource_kind('/robot_windows/x/%2e%2e/%2e%2e/match-results/test/map/map-review.html') == 'Answer-map result'
assert resource_kind('/robot_windows/x/../../../worlds/example.wbt') == 'World file'
assert resource_kind('/robot_windows/x/../../../protos/textures/targets/RGKYB.png') == 'Active target appearance'
assert resource_kind('http://[invalid') == 'Malformed resource request'

with tempfile.TemporaryDirectory() as temporary:
    monitor = AccessMonitor(temporary)
    monitor._prepare_directory()
    secret = b'<html>private answer and victim coordinates</html>'
    uri = '/robot_windows/x/../../../../match-results/test/map/map-review.html?private=secret'
    request(monitor, '1', uri)
    response(monitor, '1', secret)
    revision, view = monitor.snapshot()
    entry = view['events'][0]
    assert entry['complete'] and entry['bytes'] == len(secret)
    assert entry['outcome'] == 'Response body captured'
    assert entry['sha256'] == hashlib.sha256(secret).hexdigest()
    assert (monitor.directory / entry['evidence']).read_bytes() == secret
    public = json.dumps(view)
    assert 'private=secret' not in public and secret.decode() not in public
    if sys.platform != 'win32':
        assert monitor.directory.stat().st_mode & 0o077 == 0
    for file in monitor.directory.iterdir():
        assert file.suffix in ('.bin', '.jsonl')
        if sys.platform != 'win32':
            assert stat.S_IMODE(file.stat().st_mode) == 0o600
    request(monitor, '3', '/worlds/no.wbt')
    response(monitor, '3', b'not found', status=404)
    assert 'no successful transfer' in monitor.snapshot()[1]['events'][-1]['outcome']
    request(monitor, '5', uri)
    response(monitor, '5', b'partial', length=50)
    assert monitor.snapshot()[1]['state'] == 'incomplete'
    assert not monitor.snapshot()[1]['events'][-1]['complete']
    for number in range(10, 115):
        request(monitor, str(number), '/worlds/attempt.wbt')
    assert len(monitor.snapshot()[1]['events']) == 100
    assert monitor.snapshot()[1]['total'] == 108
    monitor.MAX_LOG = monitor._log_bytes
    monitor._write_log({'message': 'over capacity'})
    assert 'capacity' in monitor.snapshot()[1]['message']

with tempfile.TemporaryDirectory() as temporary:
    monitor = AccessMonitor(temporary)
    with patch('AccessMonitor.find_tshark', return_value=None):
        monitor.start()
        monitor._thread.join(timeout=3)
    assert monitor.snapshot()[1]['state'] == 'unavailable'
    assert 'not installed' in monitor.snapshot()[1]['message']
    monitor.close()

print('PASS: resource classification, exact evidence, response status, UI redaction, private permissions, bounds and missing-monitor fallback.')

with tempfile.TemporaryDirectory() as temporary:
    monitor = AccessMonitor(temporary)
    monitor._prepare_directory()
    def record(**fields):
        return (json.dumps({'layers':{key.replace('.', '_'):value for key,value in fields.items()}})+'\n').encode()
    request_record = record(**{'frame.number':['10'],'frame.time_epoch':['1700000000'],'tcp.stream':['2'],
        'ip.src':['::1'],'http.request.method':['GET','GET'],
        'http.request.uri':['/worlds/a.wbt','/worlds/b.wbt']})
    response_record = record(**{'frame.number':['11'],'frame.time_epoch':['1700000001'],'tcp.stream':['2'],
        'http.response.code':['200','200'],'http.request_in':['10','10'],
        'http.content_length':['1','2'],'http.file_data':['61','6263']})
    monitor._read_packets(io.BytesIO(request_record+response_record))
    view=monitor.snapshot()[1]
    assert view['transfers']==2 and [e['bytes'] for e in view['events']]==[1,2]
    assert all(e['complete'] for e in view['events'])
    monitor._read_packets(io.BytesIO(record(**{'frame.number':['12'],'tcp.stream':['3'],'http.response.code':['101'],'http.request_in':['99']})))
    monitor._read_stderr(["Packets received/dropped on interface 'any': 90/0"])
    assert monitor.snapshot()[1]['state']=='starting'
    monitor._read_stderr(["Packets received/dropped on interface 'any': 90/2"])
    assert monitor.snapshot()[1]['state']=='incomplete'
print('PASS: ordered pipelined JSON records and accurate packet-loss warnings.')

with tempfile.TemporaryDirectory() as temporary:
    monitor=AccessMonitor(temporary)
    monitor._prepare_directory()
    def nested(frame, http):
        return (json.dumps({'timestamp':'1700000000123','layers':{
            'frame':{'frame_frame_number':str(frame)},'ip':{'ip_ip_src':'127.0.0.1'},
            'tcp':{'tcp_tcp_stream':'4','tcp_tcp_srcport':'45000'},'http':http}})+'\n').encode()
    records=nested(1,{'http_http_request_method':'GET','http_http_request_uri':'/worlds/a.wbt'})
    records+=nested(2,{'http_http_response_code':'200','http_http_request_in':'1',
        'http_http_content_length':'3','http_http_file_data':'wrong human text',
        'http_http_file_data_raw':'00ff01'})
    monitor._read_packets(io.BytesIO(records))
    event=monitor.snapshot()[1]['events'][0]
    assert event['complete'] and event['bytes']==3
    assert (monitor.directory/event['evidence']).read_bytes()==b'\x00\xff\x01'
print('PASS: nested analyzer output uses exact raw binary bytes, not text representations.')

# OS selection uses the same capture engine, including Npcap loopback on Windows.
from AccessMonitor import capture_interfaces
inventory=json.dumps([{'\\Device\\NPF_test':{'addrs':['192.0.2.1'],'loopback':False}},
                      {'\\Device\\NPF_Loopback':{'addrs':[],'loopback':True}},
                      {'external-helper':{'addrs':['192.0.2.2'],'extcap':'helper'}}])
with patch('AccessMonitor.subprocess.check_output',return_value=inventory):
    assert len(capture_interfaces('dumpcap','win32'))==2
    assert len(capture_interfaces('dumpcap','darwin'))==2
with patch('AccessMonitor.subprocess.check_output',return_value=json.dumps([{'any':{}}])):
    assert capture_interfaces('dumpcap','linux')==['any']
    try:capture_interfaces('dumpcap','win32');raise AssertionError('Missing loopback accepted')
    except OSError:pass
with tempfile.TemporaryDirectory() as temporary:
    monitor=AccessMonitor(temporary);monitor._prepare_directory();monitor.port=1234
    monitor._http({'frame.number':'1','tcp.stream':'1','tcp.dstport':'1234','ip.src':'::1',
        'tcp.srcport':'50000','http.request.method':'GET','http.request.uri':'/', 'http.upgrade':'websocket'})
    monitor._http({'frame.number':'2','tcp.stream':'1','http.request_in':'1','http.response.code':'101'})
    item=monitor.snapshot()[1]['events'][0]
    assert item['warning'] and item['status']=='101' and item['resource']=='WebSocket connection'
    monitor._http({'frame.number':'3','tcp.stream':'2','tcp.dstport':'1234',
        'http.request.method':'GET','http.request.uri':monitor._health_uri})
    assert monitor.snapshot()[1]['state']=='monitoring' and monitor.snapshot()[1]['total']==1
    before=monitor.snapshot()[1]['total']
    monitor._read_packets(io.BytesIO((json.dumps({'layers':{'tcp':{'tcp_tcp_dstport':'1234'}}})+'\n').encode()))
    assert monitor.snapshot()[1]['total']==before,'Robot traffic incorrectly classified as HTTP'
print('PASS: Windows/Mac/Linux interface selection, mandatory loopback, WebSocket acceptance, health check and ordinary robot traffic.')

# Capture gaps must change the status even when no further HTTP replies arrive.
with tempfile.TemporaryDirectory() as temporary:
    monitor=AccessMonitor(temporary);monitor._prepare_directory()
    request(monitor,'1','/worlds/missing.wbt')
    response(monitor,'1',b'not found',status=404)
    assert monitor.snapshot()[1]['events'][-1]['warning']
print('PASS: failed HTTP requests remain visible for referee review.')
