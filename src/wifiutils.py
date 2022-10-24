import time
import uasyncio as asyncio
import network
import ulogging
import slutils
log = ulogging.getLogger(__name__)
log.setLevel(ulogging.DEBUG)


def _on_connect():
    log.debug("Wifi connected")


def _on_disconnect():
    log.debug("Wifi disconnected")
    _set_station(network.WLAN(network.STA_IF))
    station = _stations[0]
    if station.status() <= 1000:
        secrets = slutils.read_secrets()
        station.active(True)
        if not station.isconnected():
            if "password" in secrets["wifi"] and secrets["wifi"]["password"] != "":
                station.connect(secrets["wifi"]["ssid"],
                                secrets["wifi"]["password"])
            else:
                station.connect(secrets["wifi"]["ssid"])

        log.info("Connecting")
        c_retries = 0
        while not station.isconnected():
            log.info("Attempt %s", c_retries)
            time.sleep(1)
            c_retries += 1
    else:
        log.debug("Auto connecting")


_on_connect_callbacks = [_on_connect]
_on_disconnect_callbacks = [_on_disconnect]
_stations = []


def register_on_connect_callback(callback):
    _on_connect_callbacks.append(callback)


def un_register_on_connect_callback(callback):
    _on_connect_callbacks.remove(callback)


async def _listenForNetworkEvents():
    currentState = is_network_connected()
    while True:
        newState = is_network_connected()
        if newState != currentState:
            currentState = newState
            if currentState:
                for callback in _on_connect_callbacks:
                    callback()
            else:
                for callback in _on_disconnect_callbacks:
                    callback()
        await asyncio.sleep(5)


def listenForNetworkEvents():
    asyncio.get_event_loop().create_task(_listenForNetworkEvents())


def is_network_connected():
    station = network.WLAN(network.STA_IF)
    return station.active() and station.isconnected()


def active_station():
    if len(_stations) > 0:
        return _stations[0]
    return None


def _set_station(station):
    if len(_stations) > 0:
        _stations.pop(0)
    _stations.append(station)


def connect_sta(secrets, retries=10):
    network.WLAN(network.AP_IF).active(False)
    _set_station(network.WLAN(network.STA_IF))
    station = _stations[0]
    station.active(True)
    if not station.isconnected():
        if "password" in secrets["wifi"] and secrets["wifi"]["password"] != "":
            station.connect(secrets["wifi"]["ssid"],
                            secrets["wifi"]["password"])
        else:
            station.connect(secrets["wifi"]["ssid"])

    log.info("Connecting")
    c_retries = 0
    while not station.isconnected() and c_retries < retries:
        log.info("Attempt %s", c_retries)
        time.sleep(1)
        c_retries += 1
    return c_retries < retries


def connect_ap(secrets):
    log.info("Connection to %s timed out. Starting backup network",
             secrets["wifi"]["ssid"])
    network.WLAN(network.STA_IF).active(False)
    _set_station(network.WLAN(network.AP_IF))
    station = _stations[0]
    station.active(True)
    station.config(essid=secrets["ap"]["ssid"],
                   authmode=network.AUTH_WPA_WPA2_PSK,
                   password=secrets["ap"]["password"])
    while not station.active():
        time.sleep(1)
    return True


def connect_sta_fallback_ap(secrets):
    if not connect_sta(secrets):
        connect_ap(secrets)

    log.info("Connection successful")
    log.info("Network info %s", active_station().ifconfig())
