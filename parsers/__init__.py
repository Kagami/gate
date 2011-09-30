class Parser(object):

    features = ()

    def is_supported(self, feature):
        return feature in self.features

    def get_subscription_username(self, sub):
        return "main"

    def do_task(self, task):
        return


# Import and set parsers
from parsers.wakaba import Wakaba

parsers = {
    "wakaba": Wakaba(),
}
