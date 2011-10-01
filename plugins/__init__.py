import re
from twisted.application import service
from twisted.internet import defer
from utils import _NotHandled, trim
import config


@defer.inlineCallbacks
def command_handler(user_jid, our_jid, text):
    """Handle user's command. Return deferred."""
    text_length = len(text)
    if text_length > config.max_command_length:
        defer.returnValue(
            u"Sorry, command is too long (%d chars). "
             "Max length is %d." % (text_length, config.max_command_length))
    text = text.strip()
    for plugin in _plugins:
        try:
            result = yield plugin.handle(user_jid, our_jid, text)
        except _NotHandled:
            pass
        else:
            defer.returnValue(result)
    defer.returnValue(u"Wrong command. Try 'help'.")


class Plugin(object):
    """Base plugin class. Implements command handling."""

    show_help = False

    def __init__(self):
        self.name = self.__class__.__name__.lower()
        docs = [u"%s plugin help:" % self.name]
        # Compile handlers' regexs and create help
        self._handlers = []
        for regex, handler in self.get_handlers():
            regex = u"\A%s\Z" % regex
            self._handlers.append((re.compile(regex), handler))
            if handler.__doc__:
                docs.append(trim(handler.__doc__))
        if hasattr(self.__class__, "about"):
            docs.append(trim(self.__class__.about))
        self._help_text = u"\n\n".join(docs)

    def start(self, plugins, xmpp):
        self._plugins = plugins
        self._xmpp = xmpp

    def stop(self):
        pass

    def reload_config(self, config):
        """Called by config plugin."""

    def get_handlers(self):
        return (
            (r"[Hh]elp(?: +(\S+))?", self.help),
        )

    def handle(self, user_jid, our_jid, text):
        """Find handler for user's command via regex match.
        Raising _NotHandled means that command wasn't handled
        by plugin.
        """
        for regex, handler in self._handlers:
            match = regex.match(text)
            if match is not None:
                return handler(user_jid, our_jid, *match.groups())
        raise _NotHandled

    def help(self, user_jid, our_jid, plugin_name):
        if plugin_name and self.name == plugin_name and self.show_help:
            return self._help_text
        else:
            raise _NotHandled


class PluginsService(service.Service):

    def __init__(self, xmpp_component):
        self._xmpp = xmpp_component

    def startService(self):
        def do_class(matchobj):
            return matchobj.group().replace("_", "").upper()

        for plugin_name in config.plugins:
            class_name = re.sub(r"^.|_.", do_class, plugin_name)
            mod = __import__("plugins." + plugin_name)
            mod = getattr(mod, plugin_name)
            plugin = getattr(mod, class_name)()
            _plugins.append(plugin)
        for plugin in _plugins:
            plugin.start(_plugins, self._xmpp)

    def stopService(self):
        for plugin in _plugins:
            plugin.stop()

_plugins = []
