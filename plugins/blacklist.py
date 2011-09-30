from plugins import Plugin


class Blacklist(Plugin):
    """Implements reading blacklisted servers
    from config and passing it to xmpp component.
    """

    def reload_config(self, config):
        if not config:
            return
        data = config[0]["blacklist"]
        self._xmpp.blacklist = data.strip().split()
