import cPickle
from twisted.python import log
from twisted.internet import defer, reactor, protocol, error
from pipe_protocol import PipeProtocol
import config


class ParsingProtocol(protocol.ProcessProtocol):

    def __init__(self, xmpp):
        self._xmpp = xmpp
        self._proto = PipeProtocol()
        self._callbacks = {}
        self._id = 0

    def start(self):
        reactor.spawnProcess(self, "parsing_worker.py")

    def stop(self):
        try:
            self.transport.signalProcess("KILL")
        except error.ProcessExitedAlready:
            pass

    def outReceived(self, out):
        packets = self._proto.decode(out)
        for packet in packets:
            parsed = cPickle.loads(packet)
            self._callbacks[parsed["_id"]].callback(parsed)
            del self._callbacks[parsed["_id"]]

    def errReceived(self, err):
        report = u"PARSING WORKER ERROR:\n\n%s" % err
        log.msg(report)
        self._xmpp.send_message(
            to=config.error_report_jid, from_=config.main_full_jid,
            body=report)

    def parse(self, task, data):
        self._id += 1
        d = defer.Deferred()
        self._callbacks[self._id] = d
        task = task.copy()
        task["_id"] = self._id
        task["_data"] = data
        encoded = self._proto.encode(cPickle.dumps(task, protocol=2))
        self.transport.write(encoded)
        return d
