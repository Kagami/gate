from utils import _NotHandled, trim
from plugins import Plugin


class Help(Plugin):
    """Implements help."""

    def start(self):
        plugins_str = u", ".join(
            [p.name for p in self._plugins if p.show_help])
        self._help_text = trim(u"""Help:

            Help [plugin]
            Show this message or plugin help.
            List of plugins: %s

            All commands could be typed with or without
            initial cap i.e. 'Help' = 'help'.
            Spaces between arguments are not significant
            i.e. it's ok to type '   S     url    '.
            """ % plugins_str)

    def help(self, user_jid, our_jid, plugin_name):
        if not plugin_name:
            return self._help_text
        else:
            raise _NotHandled
