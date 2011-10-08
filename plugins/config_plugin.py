import ConfigParser
from twisted.internet import defer
from twisted.internet.threads import deferToThread
from plugins import Plugin
import utils


class ConfigPlugin(Plugin):
    """Implements getting and setting plugins configs."""

    def start(self):
        # Blockingly get config and set it. It's ok since
        # reactor has not started yet.
        config = self._blocking_get_config()
        self._reload_plugins_configs(config)

    def get_handlers(self):
        return super(ConfigPlugin, self).get_handlers() + (
            (r"[Rr]eload", self.reload_plugins_configs),
        )

    def _blocking_get_config(self):
        config = ConfigParser.RawConfigParser()
        config.read("plugins.cfg")
        return config

    def _reload_plugins_configs(self, config):
        for plugin in self._plugins:
            c = []
            for section in config.sections():
                if section.startswith(plugin.name):
                    c.append(dict(config.items(section)))
            plugin.reload_config(c)

    @utils.require_admin
    @defer.inlineCallbacks
    def reload_plugins_configs(self, user_jid, our_jid):
        config = yield deferToThread(self._blocking_get_config)
        self._reload_plugins_configs(config)
        defer.returnValue(u"Done.")
