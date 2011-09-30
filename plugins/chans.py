from plugins.subscriptions import Subscriptions
from parsers import parsers


class Chans(Subscriptions):
    """Chans plugin."""

    about = u"""Usage examples:
        S http://example.com/b/res/1947391.html
        S http://example.com/a/res/68380.html cool thread!
        U http://example.com/a/res/68380.html
        L
        D 1 not so cool
        U 1
        """

    def get_handlers(self):
        return super(Chans, self).get_handlers() + (
            (r"[Cc]hans", self.chans),
        )

    def reload_config(self, config):
        # TODO: Catch exceptions?
        self._urls_re = {}
        chans = [u"Chans:"]
        for item in config:
            parser = parsers[item["parser"]]
            r = parser.get_thread_re(item["host"])
            self._urls_re[r] = {
                "host": item["host"],
                "parser": item["parser"],
                "type": "thread",
            }
            chans.append(item["host"])
        self._chans = u"\n".join(chans)

    def url_match(self, url):
        for regex in self._urls_re:
            if regex.match(url) is not None:
                return self._urls_re[regex].copy()

    def chans(self, user_jid, our_jid):
        """Chans
        Show list of supported chans.
        """
        return self._chans
