import datetime
from twisted.internet import defer
from db_objects import *
from fetcher import get_last_modified
from plugins import Plugin
from parsers import parsers
from utils import _NotHandled, get_full_jid
import config


class Subscriptions(Plugin):
    """Implements subscirbe/unsubscribe mechanism."""

    def get_handlers(self):
        return super(Subscriptions, self).get_handlers() + (
            (r"[Ss] +(\S+)", self.subscribe),
            (r"[Uu]", self.unsubscribe),
        )

    def url_match(self, url):
        """Is url on subscribes and unsubscribes
        should be processed by this plugin.
        Return dict of fields or None.
        Redefined in subclasses.
        """

    @defer.inlineCallbacks
    def subscribe(self, user_jid, our_jid, url):
        """S <url>
        Subscribe to url.
        """
        user_subs = UserSubscriptions(user_jid)
        is_subscribed = yield user_subs.is_subscribed(url)
        if is_subscribed:
            defer.returnValue(u"You've already subscribed to this url.")
        else:
            sub = self.url_match(url)
            if type(sub) is not dict:
                raise _NotHandled
            is_too_fast = yield UserSettings(
                user_jid).is_too_fast_subscribe()
            if is_too_fast:
                defer.returnValue(u"Too many subscribe requests. "
                                   "Please, slow down.")
            try:
                yield get_last_modified(url)
            except Exception:
                defer.returnValue(
                    u"Url check failed, subscription aborted. "
                     "Seems like not existing url.")
            else:
                sub = sub.copy()
                sub["url"] = url
                parser = parsers[sub["parser"]]
                username = parser.get_subscription_username(sub)
                sub["jid"] = username + "@" + config.component_jid
                yield user_subs.subscribe(sub["url"])
                yield Subscription.save(sub)
                self._xmpp.send_presence(
                    to=user_jid, from_=sub["jid"],
                    type_="subscribe")
                self._xmpp.send_message(
                    to=user_jid, from_=get_full_jid(sub["jid"]),
                    body=u"Subscribed.")

    @defer.inlineCallbacks
    def unsubscribe(self, user_jid, our_jid):
        """U
        Unsubscribe from current url.
        """
        user_subs = UserSubscriptions(user_jid)
        url = yield Subscription.get_url_by_jid(our_jid)
        if url:
            is_subscribed = yield user_subs.is_subscribed(url)
        if url and is_subscribed:
            yield user_subs.unsubscribe(url)
            yield Subscription(url).remove_empty()
            self._xmpp.send_message(
                to=user_jid, from_=get_full_jid(our_jid),
                body="Unsubscribed.")
            self._xmpp.send_presence(
                to=user_jid, from_=our_jid,
                type_="unsubscribed")
        else:
            defer.returnValue(u"You haven't subscribed to this url.")
