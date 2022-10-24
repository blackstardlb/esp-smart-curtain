import json
import uasyncio as asyncio
import ulogging
import umqtt.simple as mqtt
import wifiutils
import constants
from bluetoothcover import BluetoothCover

log = ulogging.getLogger(__name__)
log.setLevel(ulogging.DEBUG)


class MQTTCurtain:
    def __init__(self, client: mqtt.MQTTClient, mac):
        self.client = client
        self._cover_online = None
        self.cover: BluetoothCover = BluetoothCover(
            mac, self.on_bluetooth_cover_state_changed, self.on_bluetooth_command_executed, True)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.cover.connect())
        loop.run_until_complete(self.cover.start_listening())

    def connect(self, clear=False):
        try:
            self.client.set_callback(self.on_message)
            self.client.set_last_will(
                constants.ESP_AVAILIBILITY_TOPIC, "offline", True)
            self.client.connect(clear)
            self.client.subscribe(constants.SET_COMMAND_TOPIC)
            self.client.subscribe(constants.ESP_AVAILIBILITY_TOPIC)
            self.client.subscribe(constants.SET_POSITION_TOPIC)
            self.publish_discovery_data()
            self.publish_esp_online()
        except OSError:  # type: ignore
            log.debug("Failed to connect")

    def publish_esp_online(self):
        self.publish(constants.ESP_AVAILIBILITY_TOPIC, "online", True)

    def publish_discovery_data(self):
        self.publish(
            constants.DISCOVERY_TOPIC,
            json.dumps(constants.MQTT_DISCOVERY_DATA),
            True
        )
        self.publish(
            constants.BATTERY_DISCOVERY_TOPIC,
            json.dumps(constants.MQTT_BATTERY_DISCOVERY_DATA),
            True
        )

    def on_bluetooth_cover_state_changed(self, cover: BluetoothCover):
        log.debug("Cover state changed to %s", cover.state)
        log.debug("Cover adv_state changed to %s", cover.adv_state)
        if cover.motion_status:
            self.publish(constants.STATE_TOPIC, cover.motion_status, True)
        if cover.position is not None:
            self.publish(constants.POSITION_TOPIC, f"{cover.position}", True)
        if cover.state:
            self.publish(constants.ATTRIBUTES_TOPIC,
                         json.dumps(cover.state), True)
        if cover.battery is not None:
            self.publish(constants.BATTERY_STATE_TOPIC,
                         f"{cover.battery}", True)
        if cover.adv_state:
            self.publish(constants.BATTERY_ATTRIBUTES_TOPIC,
                         json.dumps(cover.adv_state), True)

    def on_bluetooth_command_executed(self, did_succeed):
        if did_succeed != self._cover_online:
            status = "online" if did_succeed else "offline"
            if self.publish(constants.COVER_AVAILIBILITY_TOPIC, status, True):
                self._cover_online = did_succeed

    async def handle_message(self, topic: str, msg: str):
        if (topic == constants.ESP_AVAILIBILITY_TOPIC and msg != "online"):
            self.publish_esp_online()
        elif topic == constants.SET_COMMAND_TOPIC:
            await self._handle_command(msg)
        elif topic == constants.SET_POSITION_TOPIC:
            await self._handle_position(int(msg))

    async def _handle_position(self, position: int):
        await self.cover.move_to(position)

    async def _handle_command(self, command: str):
        if command == "STOP":
            await self.cover.stop()
        elif command == "OPEN":
            await self.cover.open()
        elif command == "CLOSE":
            await self.cover.close()

    def on_message(self, topic, msg):
        topic = topic.decode('UTF-8')
        msg = msg.decode('UTF-8')
        log.info("Topic: %s sent message: %s", topic, msg)
        asyncio.get_event_loop().create_task(self.handle_message(topic, msg))

    async def ping(self):
        while True:
            if wifiutils.is_network_connected():
                try:
                    self.client.ping()
                except OSError as e:  # type: ignore
                    log.exc(e, "Error while pinging")
                    self.connect()
            await asyncio.sleep(2)

    async def await_message(self):
        while True:
            if wifiutils.is_network_connected():
                try:
                    self.client.check_msg()
                except OSError as e:  # type: ignore
                    log.exc(e, "Error while awaiting message")
                    self.connect()
            await asyncio.sleep_ms(200)

    def publish(self, topic, data, persist=False):
        def sendMessage():
            try:
                log.debug("Publishing %s to %s", data, topic)
                self.client.publish(topic, data, persist)
                return True
            except (OSError, AttributeError):  # type: ignore
                log.warning("Failed to publish message to topic %s", topic)
                self.connect()
                return False
        if wifiutils.is_network_connected():
            return sendMessage()
        return False
