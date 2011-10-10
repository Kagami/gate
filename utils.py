import datetime
from twisted.internet import defer, reactor
from db_objects import *
import config


class _NotHandled(Exception):
    """By raising this exception plugin tells that he didn't
    handle the user's command.
    """


def require_admin(fn):
    """Decorator for admin commands in plugins.
    Note that user_jid argument always goes first
    (after self).
    """
    def new(self, user_jid, *args, **kwargs):
        if user_jid != config.admin_jid:
            raise _NotHandled
        else:
            return fn(self, user_jid, *args, **kwargs)
    return new


def trim(docstring):
    docstring = docstring.strip()
    return u"\n".join([line.strip() for line in docstring.splitlines()])


def get_domain(jid):
    jid = get_bare_jid(jid)
    pos = jid.find("@")
    return jid[pos+1:]


def get_bare_jid(jid):
    pos = jid.find("/")
    if pos != -1:
       jid = jid[:pos]
    return jid


def get_full_jid(jid):
    return jid + "/" + config.resource


def sleep(seconds):
    """Asynchronous sleep."""
    d = defer.Deferred()
    reactor.callLater(seconds, d.callback, None)
    return d


@defer.inlineCallbacks
def wait_for_host(host, level=1):
    """Wait if we used host less than second ago."""
    if not host in _hosts:
        _hosts[host] = {}
    while True:
        now = datetime.datetime.utcnow()
        second_ago = now - datetime.timedelta(seconds=1)
        if (not level in _hosts[host] or
            _hosts[host][level] <= second_ago):
            _hosts[host][level] = now
            break
        else:
            yield sleep(1)

_hosts = {}
