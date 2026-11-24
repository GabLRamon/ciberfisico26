"""Verificações concorrentes de DNS e HTTP e API local de status."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen
import json
import logging
import os
import socket
import time


def result(name, ok, started, detail, **extra):
    return {
        "check": name,
        "ok": bool(ok),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "latency_ms": round((monotonic() - started) * 1000, 2),
        "detail": detail,
        **extra,
    }


def check_dns(host):
    started = monotonic()
    try:
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, None, family=socket.AF_INET)})
        return result("dns", True, started, "nome resolvido", host=host, addresses=addresses)
    except OSError as exc:
        return result("dns", False, started, f"falha de resolução: {exc}", host=host, addresses=[])


def check_http(url, timeout_seconds=2.0):
    started = monotonic()
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            status = response.status
            response.read(4096)
        return result("http", 200 <= status < 400, started, f"HTTP {status}", url=url, status_code=status)
    except HTTPError as exc:
        return result("http", False, started, f"HTTP {exc.code}", url=url, status_code=exc.code)
    except OSError as exc:
        reason = getattr(exc, "reason", exc)
        return result("http", False, started, f"conexão indisponível: {reason}", url=url, status_code=None)


class MonitorState:
    def __init__(self, target_url, timeout_seconds=2.0):
        self.target_url = target_url
        self.timeout_seconds = timeout_seconds
        self.target_host = urlsplit(target_url).hostname or ""
        self._lock = Lock()
        self._snapshot = {"service": "vigianet", "checks": [], "overall_ok": False}

    def run_cycle(self):
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="probe") as pool:
            dns_future = pool.submit(check_dns, self.target_host)
            http_future = pool.submit(check_http, self.target_url, self.timeout_seconds)
            checks = [dns_future.result(), http_future.result()]
        snapshot = {
            "service": "vigianet",
            "target": self.target_url,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "overall_ok": all(item["ok"] for item in checks),
            "checks": checks,
        }
        with self._lock:
            self._snapshot = snapshot
        return snapshot

    def snapshot(self):
        with self._lock:
            return deepcopy(self._snapshot)


class StatusHandler(BaseHTTPRequestHandler):
    state = None
    server_version = "VigiaNetMonitor/1.0"
    index_file = Path(__file__).with_name("index.html")

    def do_GET(self):
        if self.path == "/status":
            if not self.index_file.exists():
                self.send_error(404, "Painel HTML não encontrado")
                return
            body = self.index_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/status/json":
            body = json.dumps(self.state.snapshot(), ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(404, "Endpoint não encontrado")

    def log_message(self, fmt, *args):
        logging.info("painel %s - %s", self.address_string(), fmt % args)
        
def monitor_loop(state, interval_seconds, log_path, stop_event):
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    while not stop_event.is_set():
        snapshot = state.run_cycle()
        line = json.dumps(snapshot, ensure_ascii=False)
        logging.info("ciclo overall_ok=%s checks=%s", snapshot["overall_ok"], line)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        stop_event.wait(interval_seconds)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    target_url = os.getenv("TARGET_URL", "http://127.0.0.1:8000/health")
    interval_seconds = max(1.0, float(os.getenv("CHECK_INTERVAL_SECONDS", "5")))
    timeout_seconds = max(0.2, float(os.getenv("REQUEST_TIMEOUT_SECONDS", "2")))
    log_path = os.getenv("LOG_PATH", "data/monitor.jsonl")
    state = MonitorState(target_url, timeout_seconds)
    stop_event = Event()
    worker = Thread(target=monitor_loop, args=(state, interval_seconds, log_path, stop_event), daemon=True)
    worker.start()

    StatusHandler.state = state
    server = ThreadingHTTPServer(("0.0.0.0", 8080), StatusHandler)
    logging.info("Painel ouvindo em 0.0.0.0:8080; alvo=%s", target_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Encerrando monitor")
    finally:
        stop_event.set()
        server.server_close()
        worker.join(timeout=3)


if __name__ == "__main__":
    main()
