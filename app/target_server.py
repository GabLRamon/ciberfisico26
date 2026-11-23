"""Serviço HTTP de exemplo que representa a aplicação da pequena empresa."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging


class TargetHandler(BaseHTTPRequestHandler):
    server_version = "VigiaNetTarget/1.0"

    def do_GET(self):
        if self.path != "/health":
            self.send_error(404, "Endpoint não encontrado")
            return
        body = json.dumps({"service": "loja-demo", "status": "ok"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        logging.info("http %s - %s", self.address_string(), fmt % args)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = ThreadingHTTPServer(("0.0.0.0", 8000), TargetHandler)
    logging.info("Alvo HTTP ouvindo em 0.0.0.0:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Encerrando alvo")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
