import traceback
from twisted.python import log
from twisted.internet import task, defer
from db_objects import *
from fetcher import NotFound, get_last_modified, get_page
from plugins import Plugin
from parsers import parsers
from parsing_protocol import ParsingProtocol
import utils
import config


class SubscriptionsUpdater(Plugin):

    MAX_CONNECTIONS_COUNT = 50
    UPDATE_TIMEOUT = 60 * 2

    def start(self):
        self._sub_worker = ParsingProtocol(self._xmpp)
        self._sub_worker.start()
        self._conn_count = 0
        self._loop = task.LoopingCall(self.run)
        self._loop.start(self.UPDATE_TIMEOUT)

    def stop(self):
        self._sub_worker.stop()

    def get_handlers(self):
        return super(SubscriptionsUpdater, self).get_handlers() + (
            (r"[Uu]pd", self.updater_info),
        )

    @utils.require_admin
    def updater_info(self, user_jid, our_jid):
        return utils.trim(u"""Updater plugin info:
            current connections count: %d
            """ % self._conn_count)

    def debug(self, msg):
        if config.log_http:
            log.msg(msg)

    @defer.inlineCallbacks
    def run(self):
        subs = yield Subscription.get_list()
        for sub in subs:
            while self._conn_count >= self.MAX_CONNECTIONS_COUNT:
                self.debug("MAX CONNECTIONS: %d, WAIT" % self._conn_count)
                yield utils.sleep(1)
            self._conn_count += 1
            parser = parsers[sub["parser"]]
            if parser.is_supported("last_modified"):
                self.process_last_modified(sub)
            else:
                self.process_page(sub, None)

    @defer.inlineCallbacks
    def process_last_modified(self, sub):
        yield utils.wait_for_host(sub["host"])
        self.debug("HOST OK: %s (last modified)" % sub["url"])
        try:
            last_modified = yield get_last_modified(sub["url"])
        except NotFound:
            self.dead_url(sub)
        except Exception:
            err = traceback.format_exc()[:-1]
            self.bad_url(sub, err)
        else:
            if last_modified:
                db_last_mod = yield Subscription(
                    sub["url"]).get_last_modified()
                if last_modified != db_last_mod:
                    # Header changed, seems like page was changed
                    # so let's continue.
                    self.debug("LAST MODIFIED WAS CHANGED: %s" % sub["url"])
                    self.process_page(sub, last_modified)
                    return
        # Exiting and decrement connections count
        self._conn_count -= 1

    @defer.inlineCallbacks
    def process_page(self, sub, last_modified):
        yield utils.wait_for_host(sub["host"])
        self.debug("HOST OK: %s (page)" % sub["url"])
        try:
            page = yield get_page(sub["url"])
        except NotFound:
            self.dead_url(sub)
        except Exception:
            err = traceback.format_exc()[:-1]
            self.bad_url(sub, err)
        else:
            parsed = yield self._sub_worker.parse(sub, page)
            self.process_parsed(sub, parsed, last_modified)
        # We've done, decrement connections count
        self._conn_count -= 1

    @defer.inlineCallbacks
    def dead_url(self, sub):
        self.debug("URL DEAD: %s" % sub["url"])
        from_ = utils.get_full_jid(sub["jid"])
        users = yield UserSubscriptions.find(sub["url"])
        yield UserSubscriptions.unsubscribe_all(sub["url"])
        yield Subscription(sub["url"]).remove()
        for user in users:
            self._xmpp.send_message(
                to=user["jid"], from_=from_,
                body=u"Url dead.")
            self._xmpp.send_presence(
                to=user["jid"], from_=sub["jid"],
                type_="unsubscribe")
            self._xmpp.send_presence(
                to=user["jid"], from_=sub["jid"],
                type_="unsubscribed")

    @defer.inlineCallbacks
    def bad_url(self, sub, err):
        num_errors = yield Host(sub["host"]).inc_errors()
        log.msg("FETCHING HOST ERROR (already %d):\n\n"
                "SUBSCRIPTION:\n%s\n\n"
                "TRACEBACK:\n%s" % (
                num_errors, sub, err))

    @defer.inlineCallbacks
    def process_parsed(self, sub, parsed, last_modified):
        if "_error" in parsed: return
        if "updates" in parsed:
            # Send updates to users
            from_ = utils.get_full_jid(sub["jid"])
            users = yield UserSubscriptions.find(sub["url"])
            for user in users:
                for text, xhtml in parsed["updates"]:
                    self._xmpp.send_message(
                        to=user["jid"], from_=from_,
                        body=text, body_xhtml=xhtml)
        # Update subscription info
        subscription = Subscription(sub["url"])
        if "last" in parsed:
            yield subscription.set_last(parsed["last"])
        if last_modified:
            yield subscription.set_last_modified(last_modified)
