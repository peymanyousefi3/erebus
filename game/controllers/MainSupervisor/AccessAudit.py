"""Portable access observations from Erebus and its existing robot window.

No packet capture or operating-system monitoring is used. Browser-relayed
Webots warnings are unverified reports, not proof of a transfer or identity.
"""
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue, Empty, Full
from threading import Event, Lock, Thread
import atexit
import json
import re
import uuid


class AccessAudit:
    MAX_LOG_BYTES = 4 * 1024 * 1024

    def __init__(self, root):
        self.session = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:12]
        self.directory = Path(root).resolve() / 'security-evidence' / self.session
        self._queue = Queue(maxsize=256)
        self._lock = Lock()
        self._stop = Event()
        self._events = deque(maxlen=100)
        self._revision = self._total = self._warnings = self._dropped = 0
        self._error = ''
        self._thread = None

    def start(self):
        self._thread = Thread(target=self._write_events, name='Erebus access audit', daemon=True)
        self._thread.start()
        atexit.register(self.close)

    def record(self, source, summary, *, warning=False, peer='', trust='server-received', **private):
        if not warning:
            return
        event = dict(time=datetime.now(timezone.utc).isoformat(), source=source,
                     summary=''.join(c if c.isprintable() else ' ' for c in str(summary))[:300],
                     warning=bool(warning), peer=str(peer)[:100], trust=trust)
        with self._lock:
            if self._stop.is_set():
                return
            try:
                self._queue.put_nowait((event, private))
            except Full:
                self._dropped += 1
                self._revision += 1
                return
            self._total += 1
            self._warnings += int(warning)
            self._events.append(event)
            self._revision += 1

    def record_command(self, command):
        # Receipt does not identify the sender or establish that execution succeeded.
        self.record('Supervisor command', str(command)[:64])

    def report_webots_warning(self, payload):
        if not isinstance(payload, str) or len(payload) > 4096:
            return False
        try:
            report = json.loads(payload)
        except (TypeError, ValueError):
            return False
        message = report.get('message') if isinstance(report, dict) else None
        if not isinstance(message, str):
            return False
        match = re.fullmatch(r'''(?:WARNING: )?Cannot read '([^\r\n]{1,2048})', sending "404 Not Found"\.''', message)
        if not match:
            return False
        filename = match[1].replace('\\', '/').rsplit('/', 1)[-1]
        self.record('Robot-window report', 'File-read warning: ' + filename,
                    warning=True, trust='browser-relayed-unverified', reported_warning=message)
        return True

    def snapshot(self):
        with self._lock:
            return self._revision, dict(session=self.session, total=self._total,
                warnings=self._warnings, dropped=self._dropped, error=self._error,
                events=list(self._events))

    def _write_events(self):
        try:
            self.directory.mkdir(parents=True, mode=0o700)
            with (self.directory / 'events.jsonl').open('x', encoding='utf-8') as log:
                written = 0
                while not self._stop.is_set() or not self._queue.empty():
                    try:
                        event, private = self._queue.get(timeout=.2)
                    except Empty:
                        continue
                    data = json.dumps(dict(event, details=private), ensure_ascii=True) + '\n'
                    if written + len(data.encode()) > self.MAX_LOG_BYTES:
                        raise OSError('Access log capacity reached; later observations are not retained.')
                    log.write(data)
                    log.flush()
                    written += len(data.encode())
        except (OSError, TypeError, ValueError) as error:
            with self._lock:
                self._error = 'Access log capacity reached; later observations are not retained.' if 'capacity reached' in str(error) else 'The access log could not be saved. Check Erebus folder permissions and storage.'
                self._revision += 1

    def close(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
