#!/usr/bin/env python3
""" Heos python lib

TODO:
    * validate soapaction replies
    * unit tests
    # remove httlib2?

"""

import socket
from select import select
from pprint import pprint
# import re
# import io
# import sys
from time import gmtime, strftime
import lxml.etree

import httplib2
# httplib2.HTTPConnectionWithTimeout.debuglevel = 5

SSDP_HOST = '239.255.255.250'
SSDP_PORT = 1900

# DENON_DEVICE = 'urn:schemas-denon-com:device:ACT-Denon:1'
DENON_DEVICE = 'urn:schemas-denon-com:device:AiosDevice:1'
MEDIA_DEVICE = 'urn:schemas-upnp-org:device:MediaRenderer:1'
AVTRANSPORT_SERVICE = 'urn:schemas-upnp-org:service:AVTransport:1'


def _get_ipaddress():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("google.com", 80))
    ipaddress = s.getsockname()[0]
    s.close()
    return ipaddress

class HttpException(Exception):
    " HttpException class "
    # pylint: disable=super-init-not-called
    def __init__(self, message):
        self.message = message


class HttpResponse(object):
    " HttpResponse "

    def __init__(self, status):
        self._headers = {}
        self._status = status
        self._add_server_header()
        self._add_date_header()

    def _add_server_header(self):
        self.add_header('Server', 'Mega Server v0.0.1')

    def _add_date_header(self):
        date = strftime("%a, %d %b %Y %H:%M:%S %Z", gmtime())
        self.add_header('Date', date)

    def add_header(self, key, value):
        " add header "
        self._headers[key] = value

    def get_headers(self):
        " get header "
        response = ""
        for header, value in self._headers.items():
            response += "{}: {}\r\n".format(header, value)
        return response

    def get_status(self):
        " get status "
        return "HTTP/1.1 {status} OK\r\n".format(status=self._status)

    def send(self, socket, content):
        headers = self.get_status() + self.get_headers() + '\r\n'
        packet = headers.encode() + content
        socket.send(packet)


class UpnpException(Exception):
    " UpnpException class "
    # pylint: disable=super-init-not-called
    def __init__(self, message):
        self.message = message


class Upnp(object):
    " Upnp class "

    def __init__(self, ssdp_host=SSDP_HOST, ssdp_port=SSDP_PORT, verbose=False):
        self._verbose = verbose
        self._ssdp_host = ssdp_host
        self._ssdp_port = ssdp_port
        self._url = None

    def discover(self, search_target, addr=None):
        " search "
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        # addr = socket.gethostname(socket.getfqdn())
        if addr:
            sock.bind((addr, self._ssdp_port))

        tmpl = ('M-SEARCH * HTTP/1.1',
                'ST: {}'.format(search_target),
                'MX: 3',
                'MAN: "ssdp:discover"',
                'HOST: ' + self._ssdp_host + ':' + str(self._ssdp_port), '', '')

        msg = "\r\n".join(tmpl).encode('ascii')
        if self._verbose:
            pprint(msg)
        sock.sendto(msg, (self._ssdp_host, self._ssdp_port))

        try:
            data = sock.recv(4096)
            if self._verbose:
                pprint(data.decode().rsplit('\r\n'))
            self._url = Upnp._parse_ssdp_location(data)
        finally:
            sock.close()
        return self._url

    def discover_mediarenderer(self, addr=None):
        " search media renderer "
        return self.discover(MEDIA_DEVICE, addr)

    def _soapaction(self, service, action, url=None, body=None):
        " soap action "
        if url is None:
            url = self._url
        if self._verbose:
            httplib2.debuglevel = 5
        http = httplib2.Http('.cache')
        header = {'Content-Type': 'text/xml; charset="utf-8"',
                  'SOAPAction': '"{}#{}"'.format(service, action)}
        _, content = http.request(url, 'POST', body=body, headers=header)
        # pprint((resp, content))
        return content

    def query_renderer(self, service, url=None):
        " query renderer "
        if url is None:
            url = self._url
        if self._verbose:
            httplib2.debuglevel = 5
        http = httplib2.Http('.cache')
        resp, content = http.request(url, headers={'cache-control':'no-cache'})
        if self._verbose:
            pprint(resp)
        # pylint: disable=no-member
        xml = lxml.etree.fromstring(content)
        # print(lxml.etree.tostring(xml, pretty_print=True).decode())
        xpath_search = '//n:service[n:serviceType="{}"]/n:controlURL/text()'.format(service)
        path = xml.xpath(xpath_search, namespaces={'n':'urn:schemas-upnp-org:device-1-0'})
        try:
            return path[0]
        except TypeError:
            raise UpnpException('Cant find renderer')

    def set_avtransport_uri(self, uri, url=None):
        " load url "
        service = AVTRANSPORT_SERVICE
        action = "SetAVTransportURI"
        body = """<?xml version="1.0" encoding="utf-8"?>
        <s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
        <s:Body>
            <u:SetAVTransportURI xmlns:u="{service}">
                <InstanceID>0</InstanceID>
                <CurrentURI>{uri}</CurrentURI>
                <CurrentURIMetaData></CurrentURIMetaData>
            </u:SetAVTransportURI>
        </s:Body>
        </s:Envelope>""".format(service=service, uri=uri)
        response_xml = self._soapaction(service, action, url, body)
        if self._verbose:
            pprint(response_xml)

    def set_play(self, url=None):
        " play "
        service = AVTRANSPORT_SERVICE
        body = """<?xml version="1.0" encoding="utf-8"?>
        <s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
        <s:Body>
            <u:Play xmlns:u="{}">
                <InstanceID>0</InstanceID>
                <Speed>1</Speed>
            </u:Play>
        </s:Body>
        </s:Envelope>""".format(service)
        response_xml = self._soapaction(service, "Play", url, body)
        if self._verbose:
            pprint(response_xml)

    @staticmethod
    def _parse_ssdp(data):
        " parse_ssdp "
        result = {}
        for line in data.decode().rsplit('\r\n'):
            try:
                key, value = line.rsplit(': ')
                result[key.lower()] = value
            # pylint: disable=bare-except
            except:
                pass
        return result

    # @staticmethod
    # def _url_to_addr(url):
    #     " _url_to_addr"
    #     import re
    #     match = re.search('https?://([^:/]+)[:/].*$', url)
    #     return match.group(1)

    @staticmethod
    def _parse_ssdp_location(data):
        " parse_ssdp_location "
        return Upnp._parse_ssdp(data)['location']


class HeosUpnp(object):
    " Heos version of Upnp "

    def __init__(self, verbose=False):
        self._verbose = verbose
        self._upnp = Upnp(verbose=verbose)
        self._url = None
        self._path = None
        self._renderer_uri = None

    def discover(self):
        " discover "
        self._url = self._upnp.discover(DENON_DEVICE)
        return self._url

    def query_renderer(self):
        " query renderer "
        if self._url is None:
            return None
        self._path = self._upnp.query_renderer(AVTRANSPORT_SERVICE, self._url)
        self._renderer_uri = self._url + self._path

    def _send_http_response(self, http_socket, content, content_type):
        " send response "
        response = HttpResponse(200)
        # response.add_header('Content-Length', content.getbuffer().nbytes)
        response.add_header('Content-Length', len(content))
        response.add_header('Content-Type', content_type)
        response.send(http_socket, content)

    # def get_request(self):
    #     " get request "
    #     try:
    #         # data = self._socket.recv(4096).decode().rsplit('\r\n')
    #         request_lines = self._socket.recv(4096).splitlines()
    #     except OSError as msg:
    #         raise HttpException(msg)

    #     request = re.match(r'GET (\w+) (HTTP/1.[01])', request_lines[0])
    #     if not request:
    #         raise HttpException('Illegal Http Request.')

    #     return request.group(1)

    def _tcp_server_non_block(self, address='0.0.0.0', port=80):
        " create tcp non blocking socket "
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((address, port))
        sock.listen(1)
        sock.setblocking(0)
        return sock

    def _tcp_accept_non_block(self, http_socket):
        client_socket = None
        while True:
            rfds, _, _ = select([http_socket], [], [])
            if http_socket in rfds:
                client_socket, address = http_socket.accept()
                if self._verbose:
                    print('[I] Got connection from {}:{}.'.format(*address))
                http_socket.close()
                break
        return client_socket

    def _play_uri(self, uri):
        " play an url "
        if not self._url:
            self.discover()
        if not self._renderer_uri:
            self.query_renderer()
        self._upnp.set_avtransport_uri(uri, self._renderer_uri)
        self._upnp.set_play(self._renderer_uri)

    def play_content(self, content, content_type='audio/mpeg', port=8888):
        " play "
        address = _get_ipaddress()
        uri = 'http://{}:{}/dummy.mp3'.format(address, port)

        http_socket = self._tcp_server_non_block(port=port)
        self._play_uri(uri)
        client_socket = self._tcp_accept_non_block(http_socket)

        # clean socket, dont care of request, sent anyway...
        client_socket.recv(1024)
        self._send_http_response(client_socket, content, content_type)
        client_socket.close()


def main():
    " main "
    # content = io.BytesIO(b'testing')
    # http = HttpServer()
    # http.serve(content, 'audio/mpeg', port=8888)
    # sys.exit(1)

    content = b''
    with open('hello.mp3', mode='rb') as f:
        content = f.read()
    content_type = 'audio/mpeg'
    http_port = 8888

    _verbose = False
    upnp = HeosUpnp(verbose=_verbose)
    url = upnp.discover()
    if _verbose:
        pprint(url)
    # upnp.discover_renderer()
    print('Query renderer')
    upnp.query_renderer()
    print('Play content')
    upnp.play_content(content, content_type, http_port)
    print('Play done')

if __name__ == "__main__":
    main()
