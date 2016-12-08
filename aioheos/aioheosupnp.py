#!/usr/bin/env python3
""" Heos python lib

TODO:
    * validate soapaction replies
    * unit tests
    # remove httlib2?

"""

import asyncio
import socket
from select import select
from pprint import pprint
# import re
# import io
# import sys
from time import gmtime, strftime
import lxml.etree

import aiohttp

SSDP_HOST = '239.255.255.250'
SSDP_PORT = 1900

# DENON_DEVICE = 'urn:schemas-denon-com:device:ACT-Denon:1'
DENON_DEVICE = 'urn:schemas-denon-com:device:AiosDevice:1'  # for dlna
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

class Http(object):

    def __init__(self, loop):
        self._loop = loop
        self._headers = {}

    def add_header(self, key, value):
        " add header "
        self._headers[key] = value

    def _add_user_agent_header(self):
        self.add_header('user_agent', 'Mega client v0.0.1')

    def get_headers(self):
        " get header "
        headers = ""
        for header, value in self._headers.items():
            headers += "{}: {}\r\n".format(header, value)
        return headers

    def _parse_uri(self, uri):
        import re

        match = re.search('https?://([^:/]+)(:([0-9]+))?(.*)$', uri)
        host = match.group(1)
        port = match.group(3)
        if port is None:
            port = 80
        path = match.group(4)
        return (host, port, path)

    @asyncio.coroutine
    def request(self, uri, method, data=None, headers={}):
        host, port, path = self._parse_uri(uri)

        method = "{method} {path} HTTP/1.0\r\n".format(method=method, path=path)
        self._add_user_agent_header()
        self._headers.update(headers)
        request = method.encode() + self.get_headers().encode() + data

        reader, writer = yield from asyncio.open_connection(host, port, self._loop)
        writer.write(request.encode())

        reply = yield from reader.read()
        writer.close()
        header = {}
        # for line in reply.readlines():

        return reply

        # b'GET / HTTP/1.1\r\nHost: 10.0.1.91:57946\r\naccept-encoding: gzip, deflate\r\ncache-control: no-cache\r\nuser-agent: Python-httplib2/0.9.2 (gzip)\r\n\r\n'


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
        headers = ""
        for header, value in self._headers.items():
            headers += "{}: {}\r\n".format(header, value)
        return headers

    def get_status(self):
        " get status "
        return "HTTP/1.1 {status} OK\r\n".format(status=self._status)


class UpnpException(Exception):
    " UpnpException class "
    # pylint: disable=super-init-not-called
    def __init__(self, message):
        self.message = message


class Upnp(object):
    " Upnp class "

    def __init__(self, loop, ssdp_host=SSDP_HOST, ssdp_port=SSDP_PORT, verbose=False):
        self._verbose = verbose
        self._loop = loop
        self._ssdp_host = ssdp_host
        self._ssdp_port = ssdp_port
        self._url = None
        # self._http = aiohttp.ClientSession(loop=loop)

    def discover(self, search_target, addr=None):
        " search "
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        # addr = socket.gethostname(socket.getfqdn())
        if addr:
            sock.bind((addr, self._ssdp_port))

        tmpl = ('M-SEARCH * HTTP/1.1',
                'HOST: ' + self._ssdp_host + ':' + str(self._ssdp_port),
                'MAN: "ssdp:discover"',
                'ST: {}'.format(search_target),
                'MX: 3',
                'USER-AGENT: OS/version UPnP/1.1 product/version',
                '', '')

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

    # b'POST /AVTransport/control HTTP/1.1\r\nHost: 10.0.1.91:57946\r\nContent-Length: 560\r\nsoapaction: "urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI"\r\naccept-encoding: gzip, deflate\r\nuser-agent: Python-httplib2/0.9.2 (gzip)\r\ncontent-type: text/xml; charset="utf-8"\r\n\r\n'
    @asyncio.coroutine
    def _soapaction(self, service, action, url=None, body=None):
        " soap action "
        if url is None:
            url = self._url
        # if self._verbose:
        #     httplib2.debuglevel = 5
        # http = httplib2.Http('.cache')
        # http = Http(self._loop)
        params = {'Content-Type': 'text/xml; charset="utf-8"',
                  'SOAPAction': '"{}#{}"'.format(service, action)}
        response = yield from self._http.post(url, data=body, params=params)
        content = yield from response.read()

        # _, content = http.request(url, 'POST', body=body, headers=headers)
        pprint((response, content))
        return content

    @asyncio.coroutine
    def query_renderer(self, service, url=None):
        " query renderer "
        if url is None:
            url = self._url
        # if self._verbose:
        #     httplib2.debuglevel = 5
        # http = httplib2.Http('.cache')
        # resp, content = http.request(url, headers={'cache-control':'no-cache'})
        # if self._verbose:
        #     pprint(resp)
        response = yield from self._http.post(url)
        content = yield from response.read()

        # _, content = http.request(url, 'POST', body=body, headers=headers)
        pprint((response, content))
        # pylint: disable=no-member
        xml = lxml.etree.fromstring(content)
        print(lxml.etree.tostring(xml, pretty_print=True).decode())
        xpath_search = '//n:service[n:serviceType="{}"]/n:controlURL/text()'.format(service)
        path = xml.xpath(xpath_search, namespaces={'n':'urn:schemas-upnp-org:device-1-0'})
        try:
            return path[0]
        except TypeError:
            raise UpnpException('Cant find renderer')

    @asyncio.coroutine
    def set_avtransport_uri(self, uri, url=None):
        " load url "
        service = AVTRANSPORT_SERVICE
        action = "SetAVTransportURI"
        body = ('<?xml version="1.0" encoding="utf-8"?>'
                '<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
                '<s:Body>'
                    '<u:SetAVTransportURI xmlns:u="{service}">'
                        '<InstanceID>0</InstanceID>'
                        '<CurrentURI>{uri}</CurrentURI>'
                        '<CurrentURIMetaData></CurrentURIMetaData>'
                    '</u:SetAVTransportURI>'
                '</s:Body>'
                '</s:Envelope>').format(service=service, uri=uri)
        response_xml = self._soapaction(service, action, url, body)
        if self._verbose:
            pprint(response_xml)

    @asyncio.coroutine
    def set_play(self, url=None):
        " play "
        service = AVTRANSPORT_SERVICE
        body = ('<?xml version="1.0" encoding="utf-8"?>'
                '<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
                '<s:Body>'
                    '<u:Play xmlns:u="{}">'
                        '<InstanceID>0</InstanceID>'
                        '<Speed>1</Speed>'
                    '</u:Play>'
                '</s:Body>'
                '</s:Envelope>').format(service)
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
            except KeyError:
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


class PlayContentServer(asyncio.Protocol):

    def __init__(self, content, content_type, verbose=False):
        self._content = content
        self._content_type = content_type
        self._transport = None
        self._verbose = verbose

    def connection_made(self, transport):
        self._transport = transport

    def data_received(self, data):
        # dont care of request, sent data anyway...
        if self._verbose:
            pprint(data)

        response = HttpResponse(200)
        # response.add_header('Content-Length', content.getbuffer().nbytes)
        response.add_header('Content-Length', len(self._content))
        response.add_header('Content-Type', self._content_type)
        headers = response.get_status() + response.get_headers() + '\r\n'
        self._transport.write(headers.encode() + self._content)
        self._transport.close()


class HeosUpnp(object):
    " Heos version of Upnp "

    def __init__(self, loop, verbose=False):
        self._verbose = verbose
        self._upnp = Upnp(loop=loop, verbose=verbose)
        self._loop = loop
        self._url = None
        self._path = None
        self._renderer_uri = None

    @asyncio.coroutine
    def _discover(self, future):
        " discover future "
        self._url = self._upnp.discover(DENON_DEVICE)
        # return self._url
        future.set_result(self._url)

    def discover(self):
        " discover "
        future = asyncio.Future()
        asyncio.ensure_future(self._discover(future))
        self._loop.run_until_complete(future)
        url = future.result()
        return url

    @asyncio.coroutine
    def _query_renderer(self):
        " query renderer "
        if self._url is None:
            return None
        self._path = self._upnp.query_renderer(AVTRANSPORT_SERVICE, self._url)
        self._renderer_uri = self._url + self._path

    def query_renderer(self):
        " query renderer "
        task = self._loop.create_task(self._query_renderer())
        self._loop.run_until_complete(task)

    @asyncio.coroutine
    def _play_uri(self, uri):
        " play an url "
        if not self._url:
            self.discover()
        if not self._renderer_uri:
            self.query_renderer()
        self._upnp.set_avtransport_uri(uri, self._renderer_uri)
        self._upnp.set_play(self._renderer_uri)
        # TODO: do better sync than this...
        yield from asyncio.sleep(0.5)

    def play_content(self, content, content_type='audio/mpeg', port=8888):
        " play "
        address = _get_ipaddress()
        uri = 'http://{}:{}/dummy.mp3'.format(address, port)

        http_server = self._loop.create_server(
                lambda: PlayContentServer(content, content_type, verbose=True),
                port=port)
        play_uri = self._loop.create_task(self._play_uri(uri))
        self._loop.run_until_complete(asyncio.wait([http_server, play_uri]))
        # self._loop.run_until_complete(play_uri)
        # self._loop.run_until_complete(http_server)


def main():
    " main "

    content = b''
    with open('hello.mp3', mode='rb') as f:
        content = f.read()
    content_type = 'audio/mpeg'
    http_port = 8888

    loop = asyncio.get_event_loop()

    _verbose = True
    upnp = HeosUpnp(loop=loop, verbose=_verbose)
    url = upnp.discover()
    if _verbose:
        pprint(url)
    print('Query renderer')
    upnp.query_renderer()
    print('Play content')
    upnp.play_content(content, content_type, http_port)
    print('Play done')

    loop.close()

if __name__ == "__main__":
    main()
