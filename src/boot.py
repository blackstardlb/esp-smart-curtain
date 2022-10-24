import gc
import esp
import ulogging
import slutils
import wifiutils

esp.osdebug(None)
gc.collect()

log = ulogging.getLogger("boot")
log.setLevel(ulogging.DEBUG)

secrets = slutils.read_secrets()

wifiutils.listenForNetworkEvents()
wifiutils.connect_sta_fallback_ap(secrets)
