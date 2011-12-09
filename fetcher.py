from twisted.internet import defer, reactor
from twisted.web import client
from twisted.web.error import Error as WebError


USER_AGENT = ("Mozilla/5.0 (Windows NT 5.1; rv:8.0) "
              "Gecko/20100101 Firefox/8.0")
TIMEOUT = 5


# Modified version of _makeGetterFactory from
# http://twistedmatrix.com/trac/browser/tags/releases/
# twisted-11.0.0/twisted/web/client.py#L506
# with connect timeout support.
def _make_factory(url, *args, **kwargs):
    scheme, host, port, path = client._parse(url)
    factory = client.HTTPClientFactory(url, *args, **kwargs)
    connect_kwargs = {}
    if "timeout" in kwargs:
        connect_kwargs["timeout"] = kwargs["timeout"]
    if scheme == "https":
        from twisted.internet import ssl
        contextFactory = ssl.ClientContextFactory()
        reactor.connectSSL(
            host, port, factory, contextFactory, **connect_kwargs)
    else:
        reactor.connectTCP(host, port, factory, **connect_kwargs)
    return factory


class NotFound(Exception):
    pass


@defer.inlineCallbacks
def get_last_modified(url):
    """Returns Last-Modified header if available
    or None.
    """
    url = str(url)
    factory = _make_factory(
        url, method="HEAD", agent=USER_AGENT,
        timeout=TIMEOUT, followRedirect=False)
    try:
        yield factory.deferred
    except WebError as e:
        if e.status == "404":
            raise NotFound
        else:
            raise
    else:
        if "last-modified" in factory.response_headers:
            defer.returnValue(
                factory.response_headers["last-modified"][0])


@defer.inlineCallbacks
def get_page(url):
    url = str(url)
    factory = _make_factory(
        url, method="GET", agent=USER_AGENT,
        timeout=TIMEOUT, followRedirect=False)
    try:
        page = yield factory.deferred
    except WebError as e:
        if e.status == "404":
            raise NotFound
        else:
            raise
    else:
        defer.returnValue(page)
