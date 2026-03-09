#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path('/Users/William/Desktop/image making pipeline')
PIPELINE = BASE_DIR / 'trex_image_pipeline.py'
JOBS_FILE = BASE_DIR / 'job_history.json'
REQ_DIR = BASE_DIR / '.runner_requests'
HOST = '127.0.0.1'
PORT = 8765

REQ_DIR.mkdir(parents=True, exist_ok=True)

jobs_lock = threading.Lock()
jobs: dict[str, dict] = {}
MAX_JOB_SECONDS = 420


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_jobs() -> None:
    global jobs
    if JOBS_FILE.exists():
        try:
            data = json.loads(JOBS_FILE.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                jobs = data
        except Exception:
            jobs = {}

    # Recover stale running jobs on restart
    changed = False
    for j in jobs.values():
        if j.get('status') == 'running':
            j['status'] = 'error'
            j['ended_at'] = now_iso()
            j['exit_code'] = j.get('exit_code') or 125
            tail = j.get('stderr_tail', '') or ''
            j['stderr_tail'] = (tail + '\nRecovered after runner restart. Previous run state was running.').strip()
            changed = True
    if changed:
        persist_jobs()


def persist_jobs() -> None:
    with jobs_lock:
        JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding='utf-8')


def run_job(job_id: str, req_file: Path) -> None:
    cmd = ['python3', str(PIPELINE), '--request-file', str(req_file)]

    with jobs_lock:
        jobs[job_id]['status'] = 'running'
        jobs[job_id]['started_at'] = now_iso()
    persist_jobs()

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=MAX_JOB_SECONDS)
        stdout = proc.stdout or ''
        stderr = proc.stderr or ''

        batch_folder = ''
        for line in stdout.splitlines():
            if line.startswith('Done. Batch folder:'):
                batch_folder = line.split(':', 1)[1].strip()
                break

        with jobs_lock:
            jobs[job_id]['ended_at'] = now_iso()
            jobs[job_id]['exit_code'] = proc.returncode
            jobs[job_id]['stdout_tail'] = '\n'.join(stdout.splitlines()[-25:])
            jobs[job_id]['stderr_tail'] = '\n'.join(stderr.splitlines()[-25:])
            jobs[job_id]['batch_folder'] = batch_folder
            jobs[job_id]['status'] = 'ok' if proc.returncode == 0 else 'error'
        persist_jobs()
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or '') if isinstance(e.stdout, str) else ''
        err = (e.stderr or '') if isinstance(e.stderr, str) else ''
        with jobs_lock:
            jobs[job_id]['ended_at'] = now_iso()
            jobs[job_id]['exit_code'] = 124
            jobs[job_id]['stdout_tail'] = '\n'.join(out.splitlines()[-25:])
            jobs[job_id]['stderr_tail'] = ('Timed out after %ss\n' % MAX_JOB_SECONDS) + '\n'.join(err.splitlines()[-25:])
            jobs[job_id]['status'] = 'error'
        persist_jobs()


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._json(200, {'ok': True})

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/health':
            return self._json(200, {'ok': True, 'service': 'local-runner'})
        if path == '/api/jobs':
            with jobs_lock:
                items = list(jobs.values())
            items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return self._json(200, {'jobs': items[:50]})
        if path.startswith('/api/jobs/'):
            job_id = path.rsplit('/', 1)[-1]
            with jobs_lock:
                j = jobs.get(job_id)
            if not j:
                return self._json(404, {'error': 'job_not_found'})
            return self._json(200, {'job': j})
        return self._json(404, {'error': 'not_found'})

    def do_POST(self):
        path = urlparse(self.path).path
        if path != '/api/run':
            return self._json(404, {'error': 'not_found'})

        try:
            length = int(self.headers.get('Content-Length', '0'))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode('utf-8'))
        except Exception:
            return self._json(400, {'error': 'invalid_json'})

        controls = (data or {}).get('controls', {}) or {}
        if str(controls.get('provider', 'openai')).lower() != 'openai':
            return self._json(400, {'error': 'only_openai_supported'})

        job_id = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
        req_file = REQ_DIR / f'{job_id}.json'
        req_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

        with jobs_lock:
            running = [j for j in jobs.values() if j.get('status') == 'running']
        if running:
            return self._json(409, {'error': 'job_already_running', 'active_job_id': running[0].get('job_id')})

        job = {
            'job_id': job_id,
            'status': 'queued',
            'created_at': now_iso(),
            'request_file': str(req_file),
            'batch_folder': '',
            'exit_code': None,
            'stdout_tail': '',
            'stderr_tail': '',
        }

        with jobs_lock:
            jobs[job_id] = job
        persist_jobs()

        t = threading.Thread(target=run_job, args=(job_id, req_file), daemon=True)
        t.start()

        return self._json(202, {'job_id': job_id, 'status': 'queued'})


def main():
    load_jobs()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f'Local runner listening on http://{HOST}:{PORT}')
    server.serve_forever()


if __name__ == '__main__':
    main()
