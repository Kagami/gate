import datetime
from twisted.internet import defer
from db_objects import *
from fetcher import get_last_modified
from plugins import Plugin
from parsers import parsers
from utils import _NotHandled
import config


class Subscriptions(Plugin):
    """Implements subscirbe/unsubscribe mechanism."""

    def get_handlers(self):
        return super(Subscriptions, self).get_handlers() + (
            (r"[Ss] +(\S+)(?: +(\S[^\n]{,99}))?", self.subscribe),
            (r"[Uu] +(\S+)", self.unsubscribe),
            (r"[Dd] +(\S+)(?: +(\S[^\n]{,99}))?", self.update_description),
            (r"[Ll]", self.list_subscriptions),
        )

    def url_match(self, url):
        """Is url on subscribes and unsubscribes
        should be processed by this plugin.
        Return dict of fields or None.
        Redefined in subclasses.
        """

    @defer.inlineCallbacks
    def subscribe(self, user_jid, our_jid, url, description):
        """S <url> [description]
        Subscribe to url.
        You could set optional description (100 chars max).
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
                yield user_subs.subscribe(sub["url"], description)
                yield Subscription.save(sub)
                defer.returnValue(u"Subscribed.")

    @defer.inlineCallbacks
    def _parse_url_or_number(self, user_jid, url_or_number):
        """Return (user_subs, url, is_subscribed, is_number) tuple:
        users_subs, UserSubscriptions instance;
        url (can be processed by number in user's subscriptions list);
        is_subscribed, is user subscribed to this url;
        is_number, is user enters number.
        """
        user_subs = UserSubscriptions(user_jid)
        try:
            number = int(url_or_number)
        except ValueError:
            url = url_or_number
            is_subscribed = yield user_subs.is_subscribed(url)
            is_number = False
        else:
            url = yield user_subs.get_url_by_number(number)
            is_subscribed = bool(url)
            is_number = True
        defer.returnValue((user_subs, url, is_subscribed, is_number))

    @defer.inlineCallbacks
    def unsubscribe(self, user_jid, our_jid, url_or_number):
        """U <url|number>
        Unsubscribe from url by url or by number in list (see L).
        """
        res = yield self._parse_url_or_number(user_jid, url_or_number)
        (user_subs, url, is_subscribed, is_number) = res
        if is_subscribed:
            yield user_subs.unsubscribe(url)
            yield Subscription(url).remove_empty()
            defer.returnValue(u"Unsubscribed.")
        else:
            defer.returnValue(u"You haven't subscribed to this url.")

    @defer.inlineCallbacks
    def update_description(self, user_jid, our_jid, url_or_number, description):
        """D <url|number> [description]
        Set or update url description (100 chars max).
        If you want to delete description just omit it.
        Instead of url, number in list can be provided (see L).
        """
        res = yield self._parse_url_or_number(user_jid, url_or_number)
        (user_subs, url, is_subscribed, is_number) = res
        if is_subscribed:
            yield user_subs.update_description(url, description)
            defer.returnValue(u"Description updated.")
        else:
            defer.returnValue(u"You haven't subscribed to this url.")

    @defer.inlineCallbacks
    def list_subscriptions(self, user_jid, our_jid):
        """L
        Show numbered subscription list.
        """
        subscriptions = yield UserSubscriptions(user_jid).get_list()
        lines = [u"Your subscriptions:"]
        for i, item in enumerate(subscriptions, start=1):
            desc = item.get("description", "")
            lines.append(u"%d. %s %s" % (i, item["url"], desc))
        defer.returnValue(u"\n".join(lines))
