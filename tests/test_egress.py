import socket
import socketserver
import threading

import pytest
from egress import connect_remote, trusted_host


@pytest.mark.parametrize('host', ['www.facebook.com', 'video.xx.fbcdn.net', 'scontent.cdninstagram.com', 'v16.tiktokcdn.com'])
def test_platform_destinations(host):
    assert trusted_host(host)


@pytest.mark.parametrize('host', ['fbcdn.net.attacker.test', 'evilfacebook.com', 'localhost', '169.254.169.254', 'example.com'])
def test_untrusted_redirect_destinations(host):
    assert not trusted_host(host)


@pytest.mark.parametrize('allowed', [True, False])
def test_managed_proxy_connect(monkeypatch, allowed):
    requests = []
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            lines = []
            while line := self.rfile.readline():
                lines.append(line)
                if line == b'\r\n':
                    break
            requests.append(b''.join(lines))
            if not allowed:
                self.wfile.write(b'HTTP/1.1 403 Forbidden\r\n\r\n')
                self.wfile.flush()
                return
            self.wfile.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            self.wfile.flush()
            assert self.rfile.read(4) == b'PING'
            self.wfile.write(b'PONG')
            self.wfile.flush()
    with socketserver.TCPServer(('127.0.0.1', 0), Handler) as proxy:
        worker = threading.Thread(target=proxy.serve_forever, daemon=True)
        worker.start()
        monkeypatch.setenv('HTTPS_PROXY', f'http://127.0.0.1:{proxy.server_address[1]}')
        try:
            if allowed:
                with connect_remote('www.facebook.com', []) as remote:
                    remote.sendall(b'PING')
                    assert remote.recv(4) == b'PONG'
            else:
                with pytest.raises(OSError, match='denied'):
                    connect_remote('www.facebook.com', [])
            assert requests[0].startswith(b'CONNECT www.facebook.com:443 HTTP/1.1\r\n')
        finally:
            proxy.shutdown()
            worker.join(timeout=2)
