#!/usr/bin/env python3
""" Heos python lib

TODO:
    * validate soapaction replies
    * unit tests
    # remove httlib2?

"""

import asyncio
import socket
from pprint import pprint
from time import gmtime, strftime
import aiohttp
import lxml.etree

SSDP_HOST = '239.255.255.250'
SSDP_PORT = 1900

# DENON_DEVICE = 'urn:schemas-denon-com:device:ACT-Denon:1'
DENON_DEVICE = 'urn:schemas-denon-com:device:AiosDevice:1'    # for dlna
MEDIA_DEVICE = 'urn:schemas-upnp-org:device:MediaRenderer:1'
AVTRANSPORT_SERVICE = 'urn:schemas-upnp-org:service:AVTransport:1'


def _get_ipaddress():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(("google.com", 80))
    ipaddress = sock.getsockname()[0]
    sock.close()
    return ipaddress


class HttpException(Exception):
    """HttpException class."""

    # pylint: disable=super-init-not-called
    def __init__(self, message):
        self.message = message


class Http():
    """HTTP."""

    def __init__(self, loop):    # pylint: disable=redefined-outer-name
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

    @staticmethod
    def _parse_uri(uri):
        import re

        match = re.search('https?://([^:/]+)(:([0-9]+))?(.*)$', uri)
        host = match.group(1)
        port = match.group(3)
        if not port:
            port = 80
        path = match.group(4)
        return (host, port, path)

    async def request(self, uri, method, data=None, headers=None):
        """ request """
        if headers is None:
            headers = {}
        host, port, path = Http._parse_uri(uri)

        method = "{method} {path} HTTP/1.0\r\n".format(
            method=method, path=path)
        self._add_user_agent_header()
        self._headers.update(headers)
        request = method.encode() + self.get_headers().encode() + data

        reader, writer = await asyncio.open_connection(
            host, port, loop=self._loop)
        writer.write(request.encode())

        reply = await reader.read()
        writer.close()
        return reply


class HttpResponse():
    """ HttpResponse """

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


class Upnp():
    " Upnp class "

    # pylint: disable=redefined-outer-name
    def __init__(self,
                 loop,
                 ssdp_host=SSDP_HOST,
                 ssdp_port=SSDP_PORT,
                 verbose=False):
        self._verbose = verbose
        self._loop = loop
        self._ssdp_host = ssdp_host
        self._ssdp_port = ssdp_port
        self._url = None
        # Backward compat
        if hasattr(asyncio, 'ensure_future'):
            self._asyncio_ensure_future = getattr(asyncio, 'ensure_future')
        else:
            self._asyncio_ensure_future = getattr(asyncio, 'async')

    class DiscoverProtocol:
        """ Discovery Protocol """

        def __init__(self, upnp, future, search_target, verbose=False):
            self._upnp = upnp
            self._future = future
            self._search_target = search_target
            self._transport = None
            self._verbose = verbose

        def connection_made(self, transport):
            """ Protocol connection made """
            if self._verbose:
                print('Connection made')
            self._transport = transport
            sock = self._transport.get_extra_info('socket')
            # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(2)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.bind(('', self._upnp.ssdp_port))

            tmpl = (
                'M-SEARCH * HTTP/1.1',
                'Host: ' + self._upnp.ssdp_host + ':' +
                str(self._upnp.ssdp_port),
                'Man: "ssdp:discover"',
                'ST: {}'.format(self._search_target),
            # 'ST: ssdp:all',
                'MX: 3',
                '',
                '')

            msg = "\r\n".join(tmpl).encode('ascii')
            self._transport.sendto(
                msg, (self._upnp.ssdp_host, self._upnp.ssdp_port))

        def datagram_received(self, data, _):
            """ datagram received """
            content = data.decode().rsplit('\r\n')

            # sock = self._transport.get_extra_info('socket')
            # if content[0].startswith('NOTIFY'):
            if content[0] == 'HTTP/1.1 200 OK':
                # pylint: disable=line-too-long
                reply = {
                    k.lower(): v
                    for k, v in
                    [item.split(': ') for item in content if ": " in item]
                }
                if self._verbose:
                    print(reply['st'])
                if reply['st'] == self._search_target:
                    url = reply['location']
                    self._future.set_result(url)
                    self._transport.close()

        def error_received(self, exc):    # pylint: disable=no-self-use
            """ error received """
            print('[E] Error received:', exc)

        def connection_lost(self, _):
            """ connection lost """
            if self._verbose:
                print("[I] Connection lost.")
            self._transport.close()

    async def discover(self, search_target, _addr=None):
        " search "
        future = asyncio.Future()
        self._asyncio_ensure_future(
            self._loop.create_datagram_endpoint(
                lambda: Upnp.DiscoverProtocol(
                    self, future, search_target, self._verbose
                ),
                family=socket.AF_INET,
                proto=socket.IPPROTO_UDP))
        await future
        self._url = future.result()
        return self._url

    async def discover_mediarenderer(self, addr=None):
        " search media renderer "
        await self.discover(MEDIA_DEVICE, addr)

    # b'POST /AVTransport/control HTTP/1.1
    #   Host: XXXX:YYYY
    #   Content-Length: 560
    #   soapaction: "urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI"
    #   accept-encoding: gzip, deflate
    #   user-agent: Python-httplib2/0.9.2 (gzip)
    #   content-type: text/xml; charset="utf-8"
    #   '
    async def _soapaction(self, service, action, url=None, body=None):
        " soap action "
        if not url:
            url = self._url

        headers = {
            'Content-Type': 'text/xml; charset="utf-8"',
            'SOAPAction': '"{}#{}"'.format(service, action)
        }

        content = ''
        with aiohttp.ClientSession(loop=self._loop) as session:
            response = await session.post(url, data=body, headers=headers)
            if response.status == 200:
                content = await response.read()
            await response.release()

        if self._verbose:
            print(content)
        return content

    async def query_renderer(self, service, url=None):
        " query renderer "
        if not url:
            url = self._url

        # query renderer
        with aiohttp.ClientSession(loop=self._loop) as session:
            response = await session.get(url)
            if response.status == 200:
                content = await response.read()
            await response.release()

        # parse
        xml = lxml.etree.fromstring(content)    # pylint: disable=no-member
        # print(lxml.etree.tostring(xml, pretty_print=True).decode())
        xpath_search = '//n:service[n:serviceType="{}"]/n:controlURL/text()'.format(
            service)
        path = xml.xpath(
            xpath_search, namespaces={'n': 'urn:schemas-upnp-org:device-1-0'})
        try:
            return path[0]
        except TypeError:
            raise UpnpException('Cant find renderer')

    async def set_avtransport_uri(self, uri, url=None):
        " load url "
        service = AVTRANSPORT_SERVICE
        action = "SetAVTransportURI"
        # pylint: disable=line-too-long,bad-continuation
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            '<s:Body>'
            '<u:SetAVTransportURI xmlns:u="{service}">'
            '<InstanceID>0</InstanceID>'
            '<CurrentURI>{uri}</CurrentURI>'
            '<CurrentURIMetaData></CurrentURIMetaData>'
            '</u:SetAVTransportURI>'
            '</s:Body>'
            '</s:Envelope>').format(
                service=service, uri=uri)
        response_xml = await self._soapaction(service, action, url, body)
        if self._verbose:
            pprint(response_xml)

    async def set_play(self, url=None):
        " play "
        service = AVTRANSPORT_SERVICE
        # pylint: disable=line-too-long,bad-continuation
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            '<s:Body>'
            '<u:Play xmlns:u="{}">'
            '<InstanceID>0</InstanceID>'
            '<Speed>1</Speed>'
            '</u:Play>'
            '</s:Body>'
            '</s:Envelope>').format(service)
        response_xml = await self._soapaction(service, "Play", url, body)
        if self._verbose:
            pprint(response_xml)

    @property
    def ssdp_host(self):
        """ return ssdp host """
        return self._ssdp_host

    @property
    def ssdp_port(self):
        """ return ssdp port """
        return self._ssdp_port


class PlayContentServer(asyncio.Protocol):
    """ Play Content Server """

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


class AioHeosUpnp():
    " Heos version of Upnp "

    def __init__(self, loop, verbose=False):
        self._verbose = verbose
        self._upnp = Upnp(loop=loop, verbose=verbose)
        self._loop = loop
        self._url = None
        self._path = None
        self._renderer_uri = None

    async def discover(self):
        " discover "
        self._url = await self._upnp.discover(DENON_DEVICE)
        return self._url

    async def query_renderer(self):
        " query renderer "
        if not self._url:
            return
        self._path = await self._upnp.query_renderer(
            AVTRANSPORT_SERVICE, self._url)
        self._renderer_uri = self._url + self._path

    async def _play_uri(self, uri):
        " play an url "
        if not self._url:
            await self.discover()
        if not self._renderer_uri:
            await self.query_renderer()
        await self._upnp.set_avtransport_uri(uri, self._renderer_uri)
        await self._upnp.set_play(self._renderer_uri)

    async def play_content(self, content, content_type='audio/mpeg', port=0):
        " play "
        address = _get_ipaddress()

        # create a listening port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', port))
        sock.listen(1)
        port = sock.getsockname()[1]

        uri = 'http://{}:{}/dummy.mp3'.format(address, port)

        # http server
        http_server = self._loop.create_server(
            lambda: PlayContentServer(content, content_type,
                                      verbose=self._verbose),
            sock=sock
        )

        # play request
        play_uri = self._loop.create_task(self._play_uri(uri))

        await asyncio.wait([http_server, play_uri])


async def main(aioloop):    # pylint: disable=redefined-outer-name
    " main "

    _verbose = True
    upnp = AioHeosUpnp(loop=aioloop, verbose=_verbose)
    url = await upnp.discover()
    if _verbose:
        pprint(url)

    print('Query renderer')
    await upnp.query_renderer()

    content = b''
    with open('hello.mp3', mode='rb') as fhello:
        content = fhello.read()
    content_type = 'audio/mpeg'
    http_port = 8888

    print('Play content')
    await upnp.play_content(content, content_type, http_port)
    print('Play done')


if __name__ == "__main__":
    # pylint: disable=invalid-name
    aioloop = asyncio.get_event_loop()
    main(aioloop)
    aioloop.close()
