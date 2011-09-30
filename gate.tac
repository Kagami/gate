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

xmpp_manager = component.buildServiceManager(
    config.component_jid,
    config.component_secret,
    "tcp:%s:%d" % (config.component_interface, config.component_port))
xmpp_manager.setServiceParent(application)

xmpp_component = XMPPComponent()
xmpp_component.setServiceParent(xmpp_manager)

plugins_service = PluginsService(xmpp_component)
plugins_service.setServiceParent(application)
