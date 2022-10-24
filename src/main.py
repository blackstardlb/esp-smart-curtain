import ulogging
import uasyncio as asyncio
import umqtt.simple as mqtt
import slutils
import wifiutils
import constants
from mqttcurtain import MQTTCurtain

log = ulogging.getLogger(__name__)
log.setLevel(ulogging.DEBUG)

loop = asyncio.get_event_loop()

async def main():
    secrets = slutils.read_secrets()
    mqtt_client = mqtt.MQTTClient(constants.CLIENT_ID,
                                  secrets["mqtt"]["host"],
                                  secrets["mqtt"]["port"],
                                  secrets["mqtt"]["user"],
                                  secrets["mqtt"]["password"],
                                  5)
    mqtt_cover = MQTTCurtain(mqtt_client, secrets["mac"])
    wifiutils.register_on_connect_callback(mqtt_cover.connect)
    mqtt_cover.connect(True)
    loop.create_task(mqtt_cover.await_message())
    loop.create_task(mqtt_cover.ping())
    loop.run_forever()

loop.create_task(main())
loop.run_forever()
