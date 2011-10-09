import re
import os


class Parser(object):

    features = ()

    def is_supported(self, feature):
        return feature in self.features

    def do_task(self, task):
        return


def load_parsers():
    """Find and load all available parsers."""
    def do_class(matchobj):
        return matchobj.group().replace("_", "").upper()

    for parser_name in os.listdir("parsers"):
        if (parser_name.startswith("_") or
            parser_name.startswith(".") or
            not parser_name.endswith(".py")):
            continue
        parser_name = parser_name[:-3]
        class_name = re.sub(r"^.|_.", do_class, parser_name)
        mod = __import__("parsers." + parser_name)
        mod = getattr(mod, parser_name)
        parsers[parser_name] = getattr(mod, class_name)()

parsers = {}
load_parsers()
