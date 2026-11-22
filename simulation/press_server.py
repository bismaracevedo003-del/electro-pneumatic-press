import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from press_simulator import PressSimulator

HMI_ROOT = Path(__file__).resolve().parent.parent / 'hmi'


class PressApplication:
    def __init__(self, port=4040):
        self.simulator = PressSimulator()
        self.http = ThreadingHTTPServer(('127.0.0.1', port), PressHandler)
        self.http.app = self
        self.stop_event = threading.Event()

    @property
    def port(self):
        return self.http.server_address[1]

    def start(self):
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        threading.Thread(target=self._simulation_loop, daemon=True).start()
        return self

    def stop(self):
        self.stop_event.set()
        self.http.shutdown()
        self.http.server_close()

    def _simulation_loop(self):
        while not self.stop_event.is_set():
            self.simulator.tick()
            time.sleep(0.1)


class PressHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filename):
        path = HMI_ROOT / filename
        if not path.is_file():
            self.send_error(404)
            return
        content = path.read_bytes()
        content_type = {
            '.html': 'text/html; charset=utf-8',
            '.js': 'text/javascript; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
        }.get(path.suffix, 'application/octet-stream')
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path == '/api/state':
            self._send_json(self.server.app.simulator.snapshot())
            return
        if self.path in ('/', '/index.html'):
            self._send_file('index.html')
            return
        if self.path == '/app.js':
            self._send_file('app.js')
            return
        if self.path == '/styles.css':
            self._send_file('styles.css')
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(length) or b'{}')
        except json.JSONDecodeError:
            self._send_json({'error': 'invalid JSON'}, 400)
            return
        simulator = self.server.app.simulator
        try:
            if self.path == '/api/buttons':
                simulator.set_buttons(body.get('button1', False), body.get('button2', False))
            elif self.path == '/api/fault':
                simulator.set_fault(body.get('fault'), body.get('active', True))
            elif self.path == '/api/pressure':
                simulator.set_pressure(body.get('bar', 6.5))
            elif self.path == '/api/reset':
                if not simulator.reset():
                    self._send_json({'error': 'reset blocked by active safety condition'}, 400)
                    return
            else:
                self.send_error(404)
                return
        except (ValueError, TypeError) as error:
            self._send_json({'error': str(error)}, 400)
            return
        self._send_json(simulator.snapshot())


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Electro-pneumatic press simulator')
    parser.add_argument('--port', type=int, default=4040)
    args = parser.parse_args()
    app = PressApplication(port=args.port).start()
    print(f'Press HMI: http://127.0.0.1:{app.port}')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.stop()


if __name__ == '__main__':
    main()
