from parsers.wakaba import Wakaba


class IichanRu(Wakaba):

    def _get_thread_node(self, node, is_first):
        if is_first:
            return node.find("body/form/div")
        else:
            return node.find("body/div")
