"""Observe Webots HTTP transfers without changing its server or robot protocol.

Packet decoding belongs to TShark. Only redacted summaries reach the robot
window; bodies and request evidence stay in a private, non-web file format.
This is detection, not an authorization boundary for same-account programs.
"""
from collections import OrderedDict, deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread
from urllib.parse import unquote, urlsplit
import atexit
import hashlib
import json
import os
import re
import shutil
import signal
import secrets
import socket
import subprocess
import sys
import time
import uuid


def resource_kind(uri):
    """Classify resources, including encoded paths; never trust browser headers."""
    try:
        path = urlsplit(uri).path
    except ValueError:
        return 'Malformed resource request'
    for _ in range(4):
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    path = path.replace('\\', '/').lower()
    if '/thumbnails/' in path:
        return 'Field preview'
    if '/textures/targets/' in path:
        return 'Active target appearance'
    if any(name in path for name in ('/match-results/', '/recordings/', '/map-results/')):
        return 'Match recording' if '/recording' in path or path.endswith('.w3d') else 'Answer-map result'
    if '/worlds/' in path or path.endswith(('.wbt', '.wbo')):
        return 'World file'
    if '/controllers/' in path or path.endswith('.proto'):
        return 'Controller or model source'
    if '..' in path.split('/'):
        return 'Project file outside robot window'
    return None


def server_port(instance_path):
    """R2025a supplies /webots/user/PORT/ (Windows: /webots-PORT/)."""
    name = instance_path.replace('\\', '/').rstrip('/').rsplit('/', 1)[-1]
    match = re.fullmatch(r'(?:webots-)?(\d+)', name)
    port = int(match[1]) if match else 0
    if not 1 <= port <= 65535:
        raise ValueError('Webots did not supply a recognizable server port')
    return port


def find_tshark():
    candidates = [shutil.which('tshark'), '/opt/homebrew/bin/tshark',
                  '/usr/local/bin/tshark', '/Applications/Wireshark.app/Contents/MacOS/tshark',
                  str(Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Wireshark/tshark.exe'),
                  str(Path(os.environ.get('ProgramW6432', 'C:/Program Files')) / 'Wireshark/tshark.exe')]
    return next((str(path) for path in candidates if path and Path(path).is_file()), None)


def capture_interfaces(tool, platform=None):
    """Use Wireshark's interface inventory on every supported operating system."""
    platform = platform or sys.platform
    data = json.loads(subprocess.check_output([tool, '-D', '-M'], text=True, timeout=10))
    interfaces = {name: details for entry in data for name, details in entry.items()
                  if not details.get('extcap')}
    if platform.startswith('linux') and 'any' in interfaces:
        return ['any']
    selected = [name for name, details in interfaces.items()
                if details.get('loopback') or details.get('addrs')]
    if not any(interfaces[name].get('loopback') for name in selected):
        raise OSError('No loopback capture interface is available. Check Npcap or capture permissions.')
    return selected


class AccessMonitor:
    MAX_BODY = 32 * 1024 * 1024
    MAX_EVIDENCE = 128 * 1024 * 1024
    MAX_LOG = 16 * 1024 * 1024

    def __init__(self, project_root, audit=None):
        self.port = 0
        self.audit = audit
        self._health_uri = "/robot_windows/MainSupervisorWindow/erebus.png?capture-check=" + secrets.token_hex(16)
        self.root = Path(project_root)
        self.session = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:12]
        self.directory = self.root / 'security-evidence' / self.session
        self._lock = Lock()
        self._stop = Event()
        self._thread = None
        self._process = None
        self._capture = None
        self._revision = 0
        self._state = 'starting'
        self._message = 'Starting the network access monitor.'
        self._events = OrderedDict()
        self._pending = OrderedDict()
        self._stderr = deque(maxlen=30)
        self._total = 0
        self._transfers = 0
        self._bytes_saved = 0
        self._log_bytes = 0
        self._gap = False
        self._drop_counts = {}

    def start(self):
        self._thread = Thread(target=self._run, name='Erebus access monitor', daemon=True)
        self._thread.start()
        atexit.register(self.close)

    def snapshot(self):
        with self._lock:
            return self._revision, dict(state=self._state, message=self._message,
                                       session=self.session, total=self._total, transfers=self._transfers,
                                       events=list(self._events.values())[-100:],
                                       dropped_packets=sum(self._drop_counts.values()) if self._drop_counts else None)

    def _status(self, state, message):
        with self._lock:
            if (state, message) == (self._state, self._message):
                return
            self._state, self._message = state, message
            self._revision += 1
        if self.audit is not None and state in ('unavailable', 'incomplete'):
            self.audit.record('Network monitor', message, warning=True, trust='capture-status')

    def _incomplete(self, reason):
        self._gap = True
        self._status('incomplete', reason)

    def _prepare_directory(self):
        self.directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.directory.parent.chmod(0o700)
        self.directory.mkdir(mode=0o700)

    def _write_log(self, entry):
        data = (json.dumps(entry, ensure_ascii=True, separators=(',', ':')) + '\n').encode()
        if self._log_bytes + len(data) > self.MAX_LOG:
            self._incomplete('Evidence log capacity reached; later events may not be retained.')
            return
        fd = os.open(self.directory / 'events.jsonl', os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, 'ab') as log:
            log.write(data)
        self._log_bytes += len(data)

    def _publish(self, key, entry, private):
        self._write_log(dict(entry, **private))
        if self.audit is not None:
            summary = entry['resource'] + ': ' + entry.get('filename', '') + ' - ' + entry['outcome']
            if entry['status']:
                summary += ' (HTTP ' + entry['status'] + '; ' + str(entry['bytes'] or 0) + ' body bytes captured)'
            self.audit.record('Network capture', summary,
                warning=entry.get('warning', True), trust='packet-capture',
                peer=entry['source'] + ':' + entry['source_port'],
                observation=entry, evidence_session=self.session)
        with self._lock:
            if key not in self._events:
                self._total += 1
            self._events[key] = entry
            self._events.move_to_end(key)
            while len(self._events) > 100:
                self._events.popitem(last=False)
            self._revision += 1

    FIELDS = ('frame.number', 'frame.time_epoch', 'ip.src', 'ipv6.src',
              'tcp.stream', 'tcp.srcport', 'http.request.method', 'http.request.uri',
              'http.response.code', 'http.request_in', 'http.content_length', 'http.file_data',
              'http.upgrade', 'tcp.dstport')

    def _http(self, fields, index=0):
        def show(name):
            return fields.get(name, '')
        number = show('frame.number')
        stream = show('tcp.stream')
        stamp = show('frame.time_epoch')
        method = show('http.request.method')
        if method:
            # Only requests to this Webots listener are in scope, not browser traffic elsewhere.
            if show('tcp.dstport') and int(show('tcp.dstport')) != self.port:
                return
            uri = show('http.request.uri')
            if uri == self._health_uri:
                if not self._gap:
                    self._status('monitoring', 'Network capture active; loopback self-check passed. Referee activity is included.')
                return
            kind = resource_kind(uri)
            websocket = show('http.upgrade').lower() == 'websocket'
            key = f'{stream}:{number}:{index}'
            entry = dict(id=key, time=stamp, source=show('ip.src') or show('ipv6.src'),
                         source_port=show('tcp.srcport'), resource='WebSocket connection' if websocket else kind or 'Webots HTTP resource', method=method,
                         filename=unquote(urlsplit(uri).path).replace('\\', '/').rsplit('/', 1)[-1][:160] if kind != 'Malformed resource request' else '[invalid URI]',
                         warning=bool(kind or websocket),
                         outcome='Connection request observed' if websocket else 'HTTP request observed', status='', bytes=None,
                         complete=False, sha256='', evidence='')
            self._pending[(stream, number, index)] = (key, entry, uri, time.monotonic())
            if len(self._pending) > 2048:
                self._pending.popitem(last=False)
                self._incomplete('Request tracking capacity reached; some replies may be unmatched.')
            safe_uri = urlsplit(uri).path[:8192] if kind != 'Malformed resource request' else '[invalid URI]'
            self._publish(key, entry, dict(request_path=safe_uri, request_frame=number))
        status = show('http.response.code')
        if not status or (100 <= int(status) < 200 and int(status) != 101):
            return
        request_frame = show('http.request_in')
        pending_key = next((key for key in self._pending if key[:2] == (stream, request_frame)), None)
        pending = self._pending.pop(pending_key, None)
        if pending is None:
            return
        key, previous, uri, requested_at = pending
        entry = dict(previous, status=status, time=stamp)
        if int(status) >= 400:
            entry['warning'] = True
        if status == '101':
            entry['outcome'] = 'WebSocket connection accepted by Webots'
            self._publish(key, entry, dict(tcp_stream=stream, response_frame=number))
            return
        declared = show('http.content_length')
        length = int(declared) if declared.isdecimal() else None
        if previous['method'] == 'HEAD':
            length = 0
        body_hex = show('http.file_data').replace(':', '')
        body = b''
        if len(body_hex) <= self.MAX_BODY * 2:
            try:
                body = bytes.fromhex(body_hex)
            except ValueError:
                self._incomplete('A response body could not be decoded; consult the evidence log.')
        else:
            self._incomplete('A response exceeded the evidence size limit; its body was not saved.')
        entry['bytes'] = len(body)
        entry['complete'] = length is not None and len(body) == length
        if 200 <= int(status) < 300:
            entry['outcome'] = 'Response body captured' if body else 'Successful response observed; no body confirmed'
            if body:
                with self._lock:
                    self._transfers += 1
            if previous.get('warning', True) and not entry['complete']:
                self._incomplete('A sensitive response body is incomplete or its length is unknown.')
            if body and previous.get('warning', True) and self._bytes_saved + len(body) <= self.MAX_EVIDENCE:
                digest = hashlib.sha256(body).hexdigest()
                filename = digest + '.bin'
                path = self.directory / filename
                if not path.exists():
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, 'wb') as saved:
                        saved.write(body)
                    self._bytes_saved += len(body)
                entry.update(sha256=digest, evidence=filename)
            elif body and previous.get('warning', True):
                self._incomplete('Evidence storage capacity reached; later bodies are not retained.')
        else:
            entry['outcome'] = 'Access attempt observed; no successful transfer confirmed'
        self._publish(key, entry, dict(declared_bytes=length,
                                      response_frame=number, tcp_stream=stream))

    def _read_packets(self, source):
        # Use the analyzer's JSON records, not media-dependent pretty XML.
        # HTTP fields remain ordered arrays for pipelined requests/responses.
        limit = self.MAX_BODY * 12 + 65536
        while True:
            line = source.readline(limit)
            if not line:
                return
            if not line.endswith(b'\n'):
                while line and not line.endswith(b'\n'):
                    line = source.readline(65536)
                self._incomplete('A decoded packet exceeded the evidence limit and was skipped.')
                continue
            record = json.loads(line.decode('utf-8', errors='replace'), object_pairs_hook=self._keep_fields)
            layers = record.get('layers')
            if not layers:
                continue
            values = {}
            for name in self.FIELDS:
                proto = name.split('.')[0]
                containers = layers.get(proto, {})
                containers = containers if isinstance(containers, list) else [containers]
                key = proto + '_' + name.replace('.', '_')
                if name == 'http.file_data':
                    key += '_raw'
                items = []
                for container in containers:
                    value = container.get(key) if isinstance(container, dict) else None
                    if value is not None:
                        items.extend(value if isinstance(value, list) else [value])
                # Explicit-field records are used by the portable regression check.
                if not items and proto not in layers:
                    items = layers.get(name.replace('.', '_'), [])
                    items = items if isinstance(items, list) else [items]
                values[name] = items
            if record.get('timestamp'):
                values['frame.time_epoch'] = [str(int(record['timestamp']) / 1000)]
            common = {name: str(items[0]) for name, items in values.items() if items and not name.startswith('http.')}
            for operation, paired in (('http.request.method', 'http.request.uri'),
                                      ('http.response.code', 'http.request_in')):
                count = len(values[operation])
                if not count:
                    continue
                if operation == 'http.response.code' and all(100 <= int(code) < 200 and int(code) != 101 for code in values[operation]):
                    continue
                ambiguous = len(values[paired]) != count
                if operation == 'http.response.code' and count > 1:
                    ambiguous |= any(len(values[name]) != count for name in ('http.content_length', 'http.file_data'))
                if ambiguous:
                    self._write_log(dict(type='coverage_warning', frame=common.get('frame.number'),
                                         operation=operation, count=count, paired_count=len(values[paired])))
                    self._incomplete('Pipelined HTTP fields could not all be correlated; body evidence is incomplete.')
                for index in range(count):
                    fields = dict(common)
                    for name, items in values.items():
                        if name.startswith('http.') and index < len(items):
                            fields[name] = str(items[index])
                    if ambiguous:
                        fields.pop('http.file_data', None)
                        fields.pop('http.content_length', None)
                    self._http(fields, index)

    @staticmethod
    def _keep_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                previous = result[key]
                result[key] = (previous if isinstance(previous, list) else [previous]) + [value]
            else:
                result[key] = value
        return result

    def _read_stderr(self, source):
        for line in source:
            line = line.strip()[:2048]
            self._stderr.append(line)
            direct = re.search(r'(\d+) packets dropped', line, re.I)
            pair = re.search(r"received/dropped on interface '([^']+)':\s*\d+/(\d+)", line, re.I)
            with self._lock:
                if direct:
                    self._drop_counts['capture'] = int(direct[1])
                if pair:
                    self._drop_counts[pair[1]] = int(pair[2])
            if (direct and int(direct[1]) > 0) or (pair and int(pair[2]) > 0):
                self._incomplete('Packet loss reported; some accesses may be missing from the log.')
            if any(text in line.lower() for text in ('permission denied', 'permission to capture', 'could not be initiated', 'operation not permitted')):
                self._status('unavailable', 'Network capture permission is missing. Match operation is unchanged.')

    def _run(self):
        try:
            self._prepare_directory()
            tool = find_tshark()
            if not tool:
                self._status('unavailable', 'TShark is not installed. Network access is not being monitored.')
                return
            self.port = port = server_port(os.environ.get('WEBOTS_INSTANCE_PATH', ''))
            if sys.platform not in ('linux', 'darwin', 'win32'):
                raise OSError('Unsupported operating system')
            dumpcap = str(Path(tool).with_name('dumpcap.exe' if sys.platform == 'win32' else 'dumpcap'))
            interfaces = capture_interfaces(dumpcap)
            command = [tool, '-l', '-n', '-r', '-', '-d', f'tcp.port=={port},http',
                       '-o', 'tcp.desegment_tcp_streams:TRUE', '-o', 'http.desegment_body:TRUE',
                       '-Y', 'http.request or http.response', '-T', 'ek', '-x',
                       '-J', 'frame ip ipv6 tcp http']
            capture = [dumpcap, '-p', '-q', '-C', str(64 * 1024 * 1024), '-N', '16384',
                       '-B', '64' if sys.platform == 'linux' else '8',
                       '-f', f'tcp port {port}',
                       '-a', 'duration:3600', '-w', '-']
            for interface in interfaces:
                capture += ['-i', interface]
            # Stream packets through pipes; retain only bounded logs and selected bodies.
            # Report exit rather than silently missing existing TCP stream handshakes.
            self._write_log(dict(type='start', time=time.time(), platform=sys.platform, port=port, interfaces=interfaces,
                                 scope='Network HTTP only; local file reads and team identity are not covered.'))
            env = dict(os.environ, TMPDIR=str(self.directory), TEMP=str(self.directory), TMP=str(self.directory))
            # Webots' bundled library search path must not override system tools.
            env.pop('LD_LIBRARY_PATH', None)
            env.pop('DYLD_LIBRARY_PATH', None)
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            self._capture = subprocess.Popen(capture, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             env=env, creationflags=flags)
            self._process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             stdin=self._capture.stdout, env=env, creationflags=flags)
            self._capture.stdout.close()
            # Decode stderr separately; parsing and file I/O never run in the game loop.
            readers = []
            for process in (self._capture, self._process):
                reader = Thread(target=self._read_stderr,
                                args=(self._decoded_stderr(process),), daemon=True)
                reader.start()
                readers.append(reader)
            Thread(target=self._health_check, args=(interfaces, dumpcap), daemon=True).start()
            self._read_packets(self._process.stdout)
            code = self._process.wait(timeout=5)
            for reader in readers:
                reader.join(timeout=2)
            if not self._stop.is_set() and self._state != 'unavailable':
                self._status('unavailable', 'Network monitoring stopped. Check capture permission, disk space and the evidence log.')
            self._write_log(dict(type='capture_stopped', returncode=code, diagnostics=list(self._stderr),
                                 time=time.time(), incomplete=self._gap,
                                 dropped_packets=sum(self._drop_counts.values()) if self._drop_counts else None))
        except Exception as error:
            self._status('unavailable', 'Network monitoring is unavailable. Match operation is unchanged.')
            try:
                self._write_log(dict(type='monitor_error', error=str(error)[:2048],
                                     diagnostics=list(self._stderr), time=time.time()))
            except OSError:
                pass
        finally:
            self._terminate()

    def _health_check(self, interfaces, dumpcap):
        # Loopback is essential: an external-interface-only capture misses local controllers.
        for _ in range(12):
            if self._stop.wait(1) or self._state == 'unavailable':
                return
            if self._state == 'monitoring':
                break
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=2) as connection:
                    connection.settimeout(2)
                    connection.sendall(('GET ' + self._health_uri + ' HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n').encode('ascii'))
                    connection.recv(4096)
            except OSError:
                pass
        if self._state == 'starting':
            self._incomplete('Loopback capture self-check failed. Direct local requests may be invisible.')
        checks = 0
        while not self._stop.wait(5):
            if self._state == 'unavailable':
                return
            if not self._gap and any(time.monotonic() - item[3] > 15 for item in list(self._pending.values())):
                self._incomplete('A requested response has not been confirmed. Capture coverage may be incomplete; inspect the log.')
            checks += 1
            if checks % 3:
                continue
            try:
                current = capture_interfaces(dumpcap)
                if set(current) != set(interfaces):
                    self._incomplete('Network interfaces changed. Reload the world to renew capture coverage.')
                    return
            except Exception:
                self._incomplete('Network interface coverage could not be checked.')
                return

    def _decoded_stderr(self, process):
        for line in iter(process.stderr.readline, b''):
            yield line.decode('utf-8', errors='replace')

    def _terminate(self):
        for process in (self._capture, self._process):
            if process is not None and process.poll() is None:
                try:
                    if sys.platform == 'win32':
                        process.terminate()
                    else:
                        process.send_signal(signal.SIGINT)
                except ProcessLookupError:
                    continue
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)

    def close(self):
        self._stop.set()
        self._state = 'stopped'
        self._terminate()
        if self._thread is not None:
            self._thread.join(timeout=3)
