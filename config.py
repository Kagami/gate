import ConfigParser


_config = ConfigParser.RawConfigParser()
_config.read("gate.cfg")
_sect = "main"


component_jid = _config.get(_sect, "component_jid")
component_interface = _config.get(_sect, "component_interface")
component_port = _config.getint(_sect, "component_port")
component_secret = _config.get(_sect, "component_secret")

main_jid = _config.get(_sect, "main_username") + "@" + component_jid
resource = _config.get(_sect, "resource")
main_full_jid = main_jid + "/" + resource

admin_jid = _config.get(_sect, "admin_jid")
error_report_jid = _config.get(_sect, "error_report_jid")
only_admin = _config.getboolean(_sect, "only_admin")

log_xmpp = _config.getboolean(_sect, "log_xmpp")
log_http = _config.getboolean(_sect, "log_http")

database_name = _config.get(_sect, "database_name")

max_command_length = _config.getint(_sect, "max_command_length")

plugins = _config.get(_sect, "plugins").strip().split()
