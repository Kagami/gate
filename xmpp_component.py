from twisted.python import log
from twisted.internet import defer
from twisted.words.xish import domish
from twisted.words.protocols.jabber import component
from db_objects import *
from utils import get_bare_jid, get_full_jid
import config
from plugins import command_handler


class XMPPComponent(component.Service):

    def _log_data_in(self, buf):
        log.msg("RECV: %r" % buf)

    def _log_data_out(self, buf):
        log.msg("SEND: %r" % buf)

    def transportConnected(self, xmlstream):
        if config.log_xmpp:
            xmlstream.rawDataInFn = self._log_data_in
            xmlstream.rawDataOutFn = self._log_data_out

    def componentConnected(self, xmlstream):
        xmlstream.addObserver("/presence", self._on_presence)
        xmlstream.addObserver("/message[@type='chat']", self._on_message)

    def is_jid_alive(self, jid):
        """Check if jid is alive i.e. corresponding url still
        exists or it's main jid which always alive.
        """
        if jid == config.main_jid:
            return True
        return Subscription.is_jid_exists(jid)

    @defer.inlineCallbacks
    def _on_presence(self, prs):
        # TODO: Save subscriptions to the database and
        # send appropriate presences to users when go
        # online/offline (service restart).
        user_jid = get_bare_jid(prs["from"])
        if config.only_admin and user_jid != config.admin_jid:
            return
        our_jid = get_bare_jid(prs["to"])
        our_full_jid = get_full_jid(our_jid)
        type_ = prs.getAttribute("type")
        is_alive = yield self.is_jid_alive(our_jid)
        send_status = False

        if type_ == "subscribe" and is_alive:
            # Approve subscribe if jid is alive
            self.send_presence(
                to=user_jid, from_=our_jid,
                type_="subscribed")
            if our_jid == config.main_jid:
                self.send_presence(
                    to=user_jid, from_=our_jid,
                    type_="subscribe")
                is_exists = yield UserSettings(user_jid).is_exists()
                if not is_exists:
                    self.send_message(
                        to=prs["from"],
                        from_=our_full_jid,
                        body=(u"Oh hai. Type 'help' (without quotes) "
                               "for help and basic info."))
            send_status = True
        if type_ == "probe" or send_status:
            self.send_presence(to=prs["from"], from_=our_full_jid)

    @defer.inlineCallbacks
    def _on_message(self, msg):
        user_jid = get_bare_jid(msg["from"])
        if config.only_admin and user_jid != config.admin_jid:
            return
        our_jid = get_bare_jid(msg["to"])
        our_full_jid = get_full_jid(our_jid)
        is_alive = yield self.is_jid_alive(our_jid)

        if (msg.body and len(msg.body.children) > 0 and
            type(msg.body.children[0]) is unicode):
            text = msg.body.children[0]
        else:
            return

        reply_msg = self.message(to=msg["from"], from_=our_full_jid)
        if is_alive:
            d = command_handler(user_jid, our_jid, text)
            d.addCallbacks(self._send_reply, self._send_error_report,
                           callbackArgs=[reply_msg],
                           errbackArgs=[reply_msg, msg])
        else:
            reply_msg.body.addContent(u"This jid is dead or doesn't exist. "
                                       "Please send commands to existing "
                                       "jids or to the main jid.")
            self.send(reply_msg)

    def _send_reply(self, reply, reply_msg):
        if reply and type(reply) is unicode:
            reply_msg.body.addContent(reply)
            self.send(reply_msg)

    def _send_error_report(self, failure, reply_msg, msg):
        """This should be called only on system-level
        errors such as database or code error. Normal errors
        like wrong user command should be processed by command
        handler.
        """
        reply_msg.body.addContent(u"Sorry, error while handling the request "
                                   "was occured. We will try to fix it as "
                                   "soon as possible.")
        self.send(reply_msg)

        report = (u"HANDLING XMPP REQUEST ERROR:\n\n"
                   "INPUT STANZA:\n%s\n\n"
                   "FAILURE:\n%s" % (msg.toXml(), failure))
        log.msg(report)
        self.send_message(
            to=config.error_report_jid, from_=config.main_full_jid,
            body=report)

    def message(self, to="", from_="", type_="chat", body="",
                body_xhtml=""):
        """Create message stanza. Return instance of domish.Element.
        If body_xhtml is specified, create xhtml-im body and add
        body_xhtml as raw xml into it.
        """
        msg = domish.Element((None, "message"))
        if to:
            msg["to"] = to
        if from_:
            msg["from"] = from_
        msg["type"] = type_
        msg.addElement("body", content=body)
        if body_xhtml:
            xhtml = domish.Element(
                ("http://jabber.org/protocol/xhtml-im", "html"))
            b = domish.Element(("http://www.w3.org/1999/xhtml", "body"))
            b.addRawXml(body_xhtml)
            xhtml.addChild(b)
            msg.addChild(xhtml)
        return msg

    def send_message(self, *args, **kwargs):
        msg = self.message(*args, **kwargs)
        self.send(msg)

    def presence(self, to="", from_="", type_=""):
        """Create presence stanza. Return instance of domish.Element."""
        prs = domish.Element((None, "presence"))
        if to:
            prs["to"] = to
        if from_:
            prs["from"] = from_
        if type_:
            prs["type"] = type_
        return prs

    def send_presence(self, *args, **kwargs):
        prs = self.presence(*args, **kwargs)
        self.send(prs)
