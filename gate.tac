# Fix sys.path so we can run application from anywhere
import os
import sys
dirname = os.path.dirname(__file__)
if dirname:
    os.chdir(dirname)
    sys.path.insert(0, ".")


from twisted.application import service
from twisted.words.protocols.jabber import component
from xmpp_component import XMPPComponent
from plugins import PluginsService
import config

application = service.Application("gate")

# Set rotateLength to 20M
from twisted.scripts._twistd_unix import ServerOptions
options = ServerOptions()
options.parseOptions()
logfilename = options.get("logfile")
if logfilename and logfilename != "-":
    from twisted.python.log import ILogObserver, FileLogObserver
    from twisted.python.logfile import LogFile
    logfile = LogFile.fromFullPath(logfilename, rotateLength=20000000)
    application.setComponent(ILogObserver, FileLogObserver(logfile).emit)

xmpp_manager = component.buildServiceManager(
    config.component_jid,
    config.component_secret,
    "tcp:%s:%d" % (config.component_interface, config.component_port))
xmpp_manager.setServiceParent(application)

xmpp_component = XMPPComponent()
xmpp_component.setServiceParent(xmpp_manager)

plugins_service = PluginsService(xmpp_component)
plugins_service.setServiceParent(application)
