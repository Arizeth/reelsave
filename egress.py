"""Restricted CONNECT proxy; direct IP pinning or managed upstream routing."""
import base64
import ipaddress
import os
import select
import socket
import socketserver
import threading
from urllib.parse import urlsplit


def public_addresses(host, port):
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Private or reserved destination blocked')
    return addresses


TRUSTED_DOMAINS = ('facebook.com', 'fbcdn.net', 'facebook.net', 'fb.watch',
                   'instagram.com', 'cdninstagram.com', 'tiktok.com', 'tiktokcdn.com',
                   'tiktokcdn-us.com', 'tiktokv.com', 'byteoversea.com', 'ibytedtos.com',
                   'ibyteimg.com', 'muscdn.com', 'musical.ly')


def trusted_host(host):
    host = host.lower()
    return any(host == domain or host.endswith('.' + domain) for domain in TRUSTED_DOMAINS)


def connect_remote(host, addresses):
    upstream = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if not upstream:
        family, kind, proto, _, address = addresses[0]
        remote = socket.socket(family, kind, proto)
        try:
            remote.settimeout(15)
            remote.connect(address)
            return remote
        except BaseException:
            remote.close()
            raise
    # Managed upstream proxies resolve hostnames themselves. Restrict every
    # CONNECT to trusted platform/CDN domains in addition to local DNS checks.
    proxy = urlsplit(upstream)
    if proxy.scheme != 'http' or not proxy.hostname:
        raise ValueError('Unsupported upstream proxy; HTTP CONNECT required')
    remote = socket.create_connection((proxy.hostname, proxy.port or 80), timeout=15)
    try:
        headers = f'CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n'
        if proxy.username is not None:
            from urllib.parse import unquote
            credentials = f'{unquote(proxy.username)}:{unquote(proxy.password or "")}'
            headers += 'Proxy-Authorization: Basic ' + base64.b64encode(credentials.encode()).decode() + '\r\n'
        remote.sendall((headers + '\r\n').encode('ascii'))
        response = bytearray()
        while not response.endswith(b'\r\n\r\n'):
            byte = remote.recv(1)
            if not byte or len(response) >= 16384:
                raise OSError('Invalid upstream response')
            response.extend(byte)
        status = bytes(response).split(b'\r\n', 1)[0].split()
        if len(status) < 2 or status[1] != b'200':
            raise OSError('Upstream proxy denied destination')
        return remote
    except BaseException:
        remote.close()
        raise


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(15)
        try:
            line = self.rfile.readline(4097).decode('ascii').strip().split()
            if len(line) != 3 or line[0] != 'CONNECT':
                raise ValueError('HTTPS required')
            host, port = line[1].rsplit(':', 1)
            if int(port) != 443 or not host or len(host) > 253 or not trusted_host(host):
                raise ValueError('Invalid destination')
            for _ in range(100):
                header = self.rfile.readline(4097)
                if len(header) > 4096:
                    raise ValueError('Header too large')
                if header in (b'\r\n', b'\n'):
                    break
            else:
                raise ValueError('Too many headers')
            addresses = public_addresses(host, 443)
            with connect_remote(host, addresses) as remote:
                self.wfile.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
                self.wfile.flush()
                while True:
                    readable, _, _ = select.select([self.connection, remote], [], [], 30)
                    if not readable:
                        return
                    for source in readable:
                        data = source.recv(65536)
                        if not data:
                            return
                        (remote if source is self.connection else self.connection).sendall(data)
        except (ValueError, OSError, UnicodeError):
            try:
                self.wfile.write(b'HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n')
            except OSError:
                pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_proxy():
    server = Server(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
