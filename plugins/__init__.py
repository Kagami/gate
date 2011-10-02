import re
from twisted.application import service
from twisted.internet import defer
from parsing_protocol import ParsingProtocol
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

    def __init__(self, plugins, xmpp, worker):
        self.name = self.__class__.__name__.lower()
        self._plugins = plugins
        self._xmpp = xmpp
        self._worker = worker
        # Compile handlers' regexs and create help
        self._handlers = []
        docs = [u"%s plugin help:" % self.name]
        for regex, handler in self.get_handlers():
            regex = u"\A%s\Z" % regex
            self._handlers.append((re.compile(regex), handler))
            if handler.__doc__:
                docs.append(trim(handler.__doc__))
        if hasattr(self, "about"):
            docs.append(trim(self.about))
        self._help_text = u"\n\n".join(docs)

    def start(self):
        pass

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
        self._worker = ParsingProtocol(xmpp_component)

    def startService(self):
        def do_class(matchobj):
            return matchobj.group().replace("_", "").upper()

        self._worker.start()
        for plugin_name in config.plugins:
            class_name = re.sub(r"^.|_.", do_class, plugin_name)
            mod = __import__("plugins." + plugin_name)
            mod = getattr(mod, plugin_name)
            plugin = getattr(mod, class_name)(
                _plugins, self._xmpp, self._worker)
            _plugins.append(plugin)
        for plugin in _plugins:
            plugin.start()

    def stopService(self):
        for plugin in _plugins:
            plugin.stop()
        self._worker.stop()

_plugins = []
