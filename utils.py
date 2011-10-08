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
def wait_for_host(host):
    while True:
        is_too_fast = yield Host(host).is_too_fast()
        if is_too_fast:
            yield sleep(1)
        else:
            break
