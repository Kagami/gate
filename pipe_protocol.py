class PipeProtocol(object):
    """Pipe protocol implementation.
    Specification:
        <packet length>|<packet><next packet length>|<packet>
    Example:
        6|packet10|new packet
    """

    def __init__(self):
        self._data = ""
        self._len = None

    def decode(self, data):
        packets = []
        self._data += data
        while True:
            if self._len is None:
                pos = self._data.find("|")
                if pos == -1: break
                self._len = int(self._data[:pos])
                self._data = self._data[pos+1:]
            if len(self._data) >= self._len:
                packet = self._data[:self._len]
                self._data = self._data[self._len:]
                self._len = None
                packets.append(packet)
            else:
                break
        return packets

    def encode(self, packet):
        if type(packet) is unicode:
            packet = packet.encode("utf-8")
        return str(len(packet)) + "|" + packet
