from plugins import Plugin


class Whitelist(Plugin):

    def reload_config(self, config):
        if not config: return
        hosts = config[0]["whitelist"].strip().split()
        self._xmpp._whitelist = hosts
