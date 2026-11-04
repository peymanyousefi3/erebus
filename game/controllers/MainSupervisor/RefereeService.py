"""Authenticated local referee window; participant robot traffic stays unchanged."""
from collections import deque
from contextlib import contextmanager
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue, Empty, Full
from threading import Event, Lock, Thread, BoundedSemaphore
from urllib.parse import quote, unquote, urlsplit
import atexit
import hmac
import http.client
import json
import os
import secrets
import re
import select
import shutil
import socket
import time
import tempfile
import webbrowser


class RefereeConnections:
    """Identify our exact upstream connections, never an entire IP or process name."""
    def __init__(self):
        self._lock = Lock()
        self._connections = deque(maxlen=512)

    @contextmanager
    def connect(self, port):
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.settimeout(15)
        connection.bind(('127.0.0.1', 0))
        entry = [connection.getsockname(), ('127.0.0.1', port), time.time() - .002, None]
        with self._lock:
            self._connections.append(entry)
        try:
            connection.connect(('127.0.0.1', port))
            yield connection
        finally:
            connection.close()
            with self._lock:
                entry[3] = time.time()

    def authorised(self, source, source_port, destination, destination_port, timestamp):
        try:
            endpoints = ((source, int(source_port)), (destination, int(destination_port)))
            try:
                timestamp = float(timestamp)
            except ValueError:
                # TShark 4.6 EK emits nanosecond ISO timestamps; Python 3.10 accepts microseconds.
                stamp = re.sub(r'(\.\d{6})\d+', r'\1', str(timestamp)).replace('Z', '+00:00')
                timestamp = datetime.fromisoformat(stamp).timestamp()
        except (TypeError, ValueError):
            return False
        with self._lock:
            return any((start, target) == endpoints and opened <= timestamp and
                       (closed is None or timestamp <= closed)
                       for start, target, opened, closed in self._connections)


class RefereeService:
    MAX_COMMAND = 1024 * 1024
    MAX_UPLOAD = 64 * 1024 * 1024

    def __init__(self, root, port, connections, audit, robot_name="robot"):
        self.robot_name = robot_name
        self.root = Path(root).resolve()
        self.webots_port = port
        self.connections = connections
        self.audit = audit
        self.token = secrets.token_urlsafe(32)
        if os.environ.get('EREBUS_ISOLATED_SERVER') == '1':
            session_file = Path(os.environ.get('EREBUS_REFEREE_SESSION_FILE', '/tmp/erebus-referee.cfg'))
            try:
                if session_file.stat().st_mode & 0o077 or session_file.is_symlink():
                    raise ValueError('Session file permissions')
                previous = urlsplit(session_file.read_text())
                match = re.fullmatch(r'/([A-Za-z0-9_-]{43})/robot_windows/MainSupervisorWindow/MainSupervisorWindow.html', previous.path)
                if previous.hostname == '127.0.0.1' and previous.port == int(os.environ.get('EREBUS_REFEREE_PORT','1241')) and match:
                    self.token = match[1]
            except (OSError, ValueError):
                pass
        self.uploader_token = secrets.token_urlsafe(32)
        self.prefix = '/' + self.token + '/'
        self.commands = Queue(maxsize=64)
        self._stop = Event()
        self._sockets = set()
        self._lock = Lock()
        self._server = None
        self._thread = None

    def start(self, open_browser=True):
        service = self
        class Server(ThreadingHTTPServer):
            daemon_threads = True
            block_on_close = False
            slots = BoundedSemaphore(32)

            def process_request(self, request, address):
                if not self.slots.acquire(blocking=False):
                    self.shutdown_request(request)
                    return
                try:
                    super().process_request(request, address)
                except Exception:
                    self.slots.release()
                    raise

            def process_request_thread(self, request, address):
                try:
                    super().process_request_thread(request, address)
                finally:
                    self.slots.release()
        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(15)

            def handle(self):
                try:
                    super().handle()
                except (BrokenPipeError, ConnectionResetError):
                    pass  # Closing a normal referee tab is not a server error.

            def log_message(self, *args):
                pass  # Never put the private session URL into Webots' broadcast console.

            def authorised(self):
                host = self.headers.get('Host', '')
                origin = self.headers.get('Origin')
                return (host == service.authority and
                        (not origin or origin == service.origin) and
                        hmac.compare_digest(self.path[:len(service.prefix)].encode(), service.prefix.encode()))

            def headers_for(self, status, kind='text/plain; charset=utf-8', length=0):
                self.send_response(status)
                self.send_header('Content-Type', kind)
                self.send_header('Content-Length', str(length))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Connection', 'close')
                self.end_headers()

            def reject(self, status=403):
                service.audit.record('Referee service', 'Unauthorised referee connection rejected',
                    warning=True, peer=self.client_address[0], trust='referee-service')
                self.headers_for(status)

            def do_HEAD(self):
                self.do_GET()

            def do_GET(self):
                # Browsers request origin-level icons without the private session path.
                # Returning no content exposes no resource and is not an access incident.
                if urlsplit(self.path).path in ('/favicon.ico', '/apple-touch-icon.png', '/apple-touch-icon-precomposed.png'):
                    self.headers_for(204)
                    return
                if not self.authorised():
                    self.reject()
                    return
                path = unquote(urlsplit(self.path[len(service.prefix):]).path)
                if self.headers.get('Upgrade', '').lower() == 'websocket' and path == '':
                    self.websocket()
                    return
                if path == 'status':
                    body = json.dumps({'url':service.url}).encode()
                    self.headers_for(200, 'application/json', len(body))
                    if self.command != 'HEAD':
                        self.wfile.write(body)
                    return
                if path.startswith('robot_windows/MainSupervisorWindow/'):
                    base = service.root / 'game/plugins/robot_windows/MainSupervisorWindow'
                    relative = path[len('robot_windows/MainSupervisorWindow/'):]
                elif path.startswith('reports/'):
                    base = service.root / 'match-results'
                    relative = path[len('reports/'):]
                else:
                    self.headers_for(404)
                    return
                target = (base / relative).resolve()
                try:
                    target.relative_to(base.resolve())
                    if not target.is_file():
                        raise OSError('Not a file')
                    kind = {'.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8',
                            '.css':'text/css; charset=utf-8', '.png':'image/png', '.jpg':'image/jpeg',
                            '.svg':'image/svg+xml', '.json':'application/json', '.zip':'application/zip'}.get(target.suffix.lower())
                    if not kind:
                        self.headers_for(404)
                        return
                    if relative == 'MainSupervisorWindow.html':
                        html = target.read_text(encoding='utf-8')
                        metadata = '<script>window.erebusReferee=' + json.dumps({'base':service.prefix, 'reconnect':os.environ.get('EREBUS_ISOLATED_SERVER') == '1'}) + ';</script>'
                        body = html.replace('<head>', '<head>' + metadata, 1).encode('utf-8')
                        self.headers_for(200, kind, len(body))
                        if self.command != 'HEAD':
                            self.wfile.write(body)
                    else:
                        with target.open('rb') as file:
                            self.headers_for(200, kind, target.stat().st_size)
                            if self.command != 'HEAD':
                                shutil.copyfileobj(file, self.wfile)
                    service.audit.record('Referee interface', 'Opened ' + target.name,
                                         trust='referee-authorised')
                except (OSError, ValueError):
                    self.headers_for(404)

            def do_POST(self):
                if not self.authorised():
                    self.reject()
                    return
                path = self.path[len(service.prefix):]
                raw_length = self.headers.get('Content-Length', '')
                if not raw_length.isdecimal():
                    self.headers_for(411)
                    return
                length = int(raw_length)
                if path == 'commands':
                    if length > service.MAX_COMMAND:
                        self.headers_for(413)
                        return
                    try:
                        command = self.rfile.read(length).decode('utf-8')
                        if len(command.encode('utf-8')) != length:
                            raise ValueError('Incomplete command')
                        service.commands.put_nowait(command)
                    except (UnicodeError, ValueError):
                        self.headers_for(400)
                        return
                    except Full:
                        self.headers_for(429)
                        return
                    self.headers_for(202)
                elif path.startswith('uploader/'):
                    if length > service.MAX_UPLOAD:
                        self.headers_for(413)
                        return
                    client = http.client.HTTPConnection('127.0.0.1', 60520, timeout=30)
                    try:
                        client.putrequest('POST', '/' + path[len('uploader/'):])
                        client.putheader('Content-Length', str(length))
                        client.putheader('Content-Type', self.headers.get('Content-Type', 'application/octet-stream'))
                        client.putheader('X-Erebus-Referee', service.uploader_token)
                        client.endheaders()
                        remaining = length
                        while remaining:
                            data = self.rfile.read(min(65536, remaining))
                            if not data:
                                raise OSError('Incomplete upload')
                            client.send(data)
                            remaining -= len(data)
                        response = client.getresponse()
                        body = response.read(service.MAX_COMMAND)
                        self.headers_for(response.status, 'text/html; charset=utf-8', len(body))
                        self.wfile.write(body)
                    except (OSError, http.client.HTTPException):
                        self.headers_for(502)
                    finally:
                        client.close()
                else:
                    self.headers_for(404)

            def websocket(self):
                try:
                    with service.connections.connect(service.webots_port) as backend:
                        headers = ['GET / HTTP/1.1', 'Host: 127.0.0.1:' + str(service.webots_port),
                                   'Upgrade: websocket', 'Connection: Upgrade']
                        for name in ('Sec-WebSocket-Key', 'Sec-WebSocket-Version'):
                            value = self.headers.get(name)
                            if not value:
                                self.headers_for(400)
                                return
                            headers.append(name + ': ' + value)
                        backend.sendall(('\r\n'.join(headers) + '\r\n\r\n').encode('ascii'))
                        response = bytearray()
                        while b'\r\n\r\n' not in response:
                            data = backend.recv(4096)
                            if not data or len(response) > 65536:
                                raise OSError('Invalid WebSocket upgrade')
                            response.extend(data)
                        self.connection.sendall(response)
                        if not response.startswith(b'HTTP/1.1 101 '):
                            return
                        with service._lock:
                            service._sockets.update((self.connection, backend))
                        try:
                            while not service._stop.is_set():
                                readable, _, _ = select.select((self.connection, backend), (), (), 1)
                                for source in readable:
                                    data = source.recv(65536)
                                    if not data:
                                        return
                                    (backend if source is self.connection else self.connection).sendall(data)
                        finally:
                            with service._lock:
                                service._sockets.difference_update((self.connection, backend))
                except (OSError, ValueError):
                    return

        isolated = os.environ.get('EREBUS_ISOLATED_SERVER') == '1'
        port = int(os.environ.get('EREBUS_REFEREE_PORT', '1241')) if isolated else 0
        self._server = Server(('0.0.0.0' if isolated else '127.0.0.1', port), Handler)
        self.authority = '127.0.0.1:' + str(self._server.server_port)
        self.origin = 'http://' + self.authority
        self.url = self.origin + self.prefix + 'robot_windows/MainSupervisorWindow/MainSupervisorWindow.html?name=' + quote(self.robot_name, safe='')
        self._thread = Thread(target=self._server.serve_forever, name='Erebus referee interface', daemon=True)
        self._thread.start()
        atexit.register(self.close)
        if isolated:
            session_file = Path(os.environ.get('EREBUS_REFEREE_SESSION_FILE', '/tmp/erebus-referee.cfg'))
            with tempfile.NamedTemporaryFile(mode='w', dir='/tmp', prefix='.erebus-referee-', delete=False) as output:
                output.write(self.url)
            os.replace(output.name, session_file)
        elif open_browser:
            self.open_url(self.url)

    def open_url(self, url):
        def launch():
            try:
                if not webbrowser.open_new_tab(url):
                    self.audit.record('Referee service', 'The authenticated referee window could not be opened.',
                                      warning=True, trust='referee-service')
            except Exception:
                self.audit.record('Referee service', 'The authenticated referee window could not be opened.',
                                  warning=True, trust='referee-service')
        Thread(target=launch, daemon=True).start()

    def open_report(self, path):
        relative = Path(path).resolve().relative_to(self.root / 'match-results')
        self.open_url(self.origin + self.prefix + 'reports/' + quote(relative.as_posix()))

    def receive_commands(self):
        for _ in range(64):
            if self._stop.is_set():
                return
            try:
                yield self.commands.get_nowait()
            except Empty:
                return

    def close(self):
        if self._stop.is_set():
            return
        self._stop.set()
        with self._lock:
            for connection in self._sockets:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2)
