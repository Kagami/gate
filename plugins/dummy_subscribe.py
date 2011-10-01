from plugins import Plugin


class DummySubscribe(Plugin):
    """If no one plugin matches url write that
    url is wrong.
    """

    def get_handlers(self):
        return super(DummySubscribe, self).get_handlers() + (
            (r"[Ss] +(\S+)", self.subscribe),
        )

    def subscribe(self, user_jid, our_jid, url):
        return (u"Wrong url. Info about supported urls "
                 "you can get in appropriate plugin's help.")
