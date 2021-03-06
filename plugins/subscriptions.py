from twisted.internet import defer
from db_objects import *
from fetcher import get_page
from plugins import Plugin
from parsers import parsers
from utils import _NotHandled, get_full_jid, wait_for_host
import config


class Subscriptions(Plugin):
    """Implements subscirbe/unsubscribe mechanism."""

    MAX_SUBSCRIPTIONS_COUNT = 20

    def get_handlers(self):
        return super(Subscriptions, self).get_handlers() + (
            (r"[Ss] +(\S+)", self.subscribe),
            (r"[Uu](?: +(\S+))?", self.unsubscribe),
            (r"[Ll]", self.list_subscriptions),
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
        subs_count = yield user_subs.count()
        if subs_count >= self.MAX_SUBSCRIPTIONS_COUNT:
            defer.returnValue(
                u"Sorry, %d subscriptions max." % (
                    self.MAX_SUBSCRIPTIONS_COUNT))
        is_subscribed = yield user_subs.is_subscribed(url)
        if is_subscribed:
            defer.returnValue(u"You've already subscribed to this url.")
        else:
            sub = self.url_match(url)
            if type(sub) is not dict:
                raise _NotHandled
            sub = sub.copy()
            sub["url"] = url
            parser = parsers[sub["parser"]]
            username = parser.get_subscription_username(sub)
            sub["jid"] = username + "@" + config.component_jid
            last = yield Subscription(url).get_last()
            self.process_last(user_jid, our_jid, sub, last)

    @defer.inlineCallbacks
    def process_last(self, user_jid, our_jid, sub, last):
        if last is not None:
            sub["last"] = last
            yield UserSubscriptions(user_jid).subscribe(sub["url"])
            yield Subscription.create(sub)
            self._xmpp.send_presence(
                to=user_jid, from_=sub["jid"],
                type_="subscribe")
        else:
            yield wait_for_host(sub["host"], level=2)
            try:
                page = yield get_page(sub["url"])
            except Exception:
                self._xmpp.send_message(
                    to=user_jid, from_=get_full_jid(our_jid),
                    body=u"Url check failed, subscription aborted. "
                          "Seems like not existing url.")
            else:
                parsed = yield self._worker.parse(sub, page)
                if "last" in parsed and parsed["last"] is not None:
                    self.process_last(user_jid, our_jid, sub, parsed["last"])
                else:
                    self._xmpp.send_message(
                        to=user_jid, from_=get_full_jid(our_jid),
                        body=u"Page parsing failed, subscription aborted. "
                              "Seems like not existing url.")

    @defer.inlineCallbacks
    def unsubscribe(self, user_jid, our_jid, url):
        """U [url]
        Unsubscribe from current or given url.
        """
        user_subs = UserSubscriptions(user_jid)
        if not url:
            url = yield Subscription.get_url_by_jid(our_jid)
            sub_jid = our_jid
        else:
            sub_jid = yield Subscription(url).get_jid()
        if url:
            is_subscribed = yield user_subs.is_subscribed(url)
        if url and is_subscribed:
            yield user_subs.unsubscribe(url)
            yield Subscription(url).remove_empty()
            self._xmpp.send_presence(
                to=user_jid, from_=sub_jid,
                type_="unsubscribe")
            self._xmpp.send_presence(
                to=user_jid, from_=sub_jid,
                type_="unsubscribed")
        else:
            defer.returnValue(u"You haven't subscribed to this url.")

    @defer.inlineCallbacks
    def list_subscriptions(self, user_jid, our_jid):
        """L
        Show your subscriptions list.
        """
        subscriptions = yield UserSubscriptions(user_jid).get_list()
        lines = [u"Your subscriptions:"]
        lines.extend([sub["url"] for sub in subscriptions])
        defer.returnValue(u"\n".join(lines))
