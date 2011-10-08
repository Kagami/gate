from twisted.internet import defer
from plugins.subscriptions import Subscriptions
from fetcher import get_page
from parsers import parsers
import utils


class Chans(Subscriptions):
    """Chans plugin."""

    show_help = True
    about = u"""Usage example:
        S http://example.com/b/res/1947391.html
        U
        """

    def get_handlers(self):
        return super(Chans, self).get_handlers() + (
            (r"[Cc]hans", self.chans),
            (r"[Bb](?: +(\S+) +(\S+))?", self.show_board),
        )

    def reload_config(self, config):
        # TODO: Catch errors?
        self._chans = {}
        self._urls_re = {}
        for item in config:
            self._chans[item["host"]] = item["parser"]
            parser = parsers[item["parser"]]
            r = parser.get_thread_re(item["host"])
            self._urls_re[r] = {
                "host": item["host"],
                "parser": item["parser"],
                "type": "thread",
            }
        self._chans_str = u"Chans:\n" + u"\n".join(self._chans.keys())

    def url_match(self, url):
        for regex in self._urls_re:
            if regex.match(url) is not None:
                return self._urls_re[regex].copy()

    def chans(self, user_jid, our_jid):
        """Chans
        Show list of supported chans.
        """
        return self._chans_str

    # TODO: Limit max connections count, shaping user's requests.
    @defer.inlineCallbacks
    def show_board(self, user_jid, our_jid, host, board):
        """B [<chan> <board>]
        Show board's threads.
        """
        if host not in self._chans:
            defer.returnValue(u"Sorry, this chan not supported.")
        parser = parsers[self._chans[host]]
        url = parser.get_board_url(host, board)
        if not url:
            defer.returnValue(u"Wrong board.")
        yield utils.wait_for_host(host)
        try:
            page = yield get_page(url)
        except Exception:
            defer.returnValue(u"Url fetching failed.")
        defer.returnValue(u"nyak!" + unicode(len(page)))
