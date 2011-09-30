#!/usr/bin/env python

import os
import sys
import time
import fcntl
import select
import cPickle
import traceback
from parsers import parsers
from utils import PipeProtocol


# Set stdin in nonblocking-mode
fd = sys.stdin.fileno()
fl = fcntl.fcntl(fd, fcntl.F_GETFL)
fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

proto = PipeProtocol()
while True:
    select.select([sys.stdin], [], [])
    data = sys.stdin.read()
    packets = proto.decode(data)
    for packet in packets:
        task = cPickle.loads(packet)

        try:
            res = parsers[task["parser"]].do_task(task)
            if not res:
                res = {}
        except Exception:
            del task["_data"]
            err = "TASK:\n%s\n\nTRACEBACK:\n%s" % (
                repr(task), traceback.format_exc()[:-1])
            sys.stderr.write(err)
            res = {}
        res["_id"] = task["_id"]

        encoded = proto.encode(cPickle.dumps(res, protocol=2))
        sys.stdout.write(encoded)
        sys.stdout.flush()
    time.sleep(0.001)
