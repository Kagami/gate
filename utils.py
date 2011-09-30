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


class PipeProtocol(object):
    """Pipe protocol implementation.
    Specification:
        <packet length>|<packet><next packet length>|<packet>
    Example:
        6|packet10|new packet
    """

    def __init__(self):
        self._data = ""
        self._len = None

    def decode(self, data):
        packets = []
        self._data += data
        while True:
            if self._len is None:
                pos = self._data.find("|")
                if pos == -1: break
                self._len = int(self._data[:pos])
                self._data = self._data[pos+1:]
            if len(self._data) >= self._len:
                packet = self._data[:self._len]
                self._data = self._data[self._len:]
                self._len = None
                packets.append(packet)
            else:
                break
        return packets

    def encode(self, packet):
        if type(packet) is unicode:
            packet = packet.encode("utf-8")
        return str(len(packet)) + "|" + packet
