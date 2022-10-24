try:
    import bluetooth  # type: ignore
except ImportError:  # type: ignore
    import ubluetooth as bluetooth
import machine
import ubinascii

CLIENT_ID = ubinascii.hexlify(machine.unique_id()).decode('utf-8')
DISCOVERY_TOPIC = f"homeassistant/cover/{CLIENT_ID}/cover/config"
BATTERY_DISCOVERY_TOPIC = f"homeassistant/sensor/{CLIENT_ID}/sensor/config"
ATTRIBUTES_TOPIC = f"esp32/{CLIENT_ID}/cover/attributes"
BATTERY_ATTRIBUTES_TOPIC = f"esp32/{CLIENT_ID}/battery/attributes"
BATTERY_STATE_TOPIC = f"esp32/{CLIENT_ID}/battery/state"
POSITION_TOPIC = f"esp32/{CLIENT_ID}/cover/position"
STATE_TOPIC = f"esp32/{CLIENT_ID}/cover/state"
SET_POSITION_TOPIC = f"esp32/{CLIENT_ID}/cover/set_position"
SET_COMMAND_TOPIC = f"esp32/{CLIENT_ID}/cover/set"
ESP_AVAILIBILITY_TOPIC = f"esp32/{CLIENT_ID}/esp_availibility"
COVER_AVAILIBILITY_TOPIC = f"esp32/{CLIENT_ID}/cover_availibility"
MQTT_DEVICE = {
    "identifiers": [f"esp32_{CLIENT_ID}"],
    "manufacturer": "blackstardlb",
    "model": "esp32 switch bot cover hub",
    "name": "Switch Bot Curtain"
}
MQTT_DISCOVERY_DATA = {
    "availability": [
        {
            "topic": ESP_AVAILIBILITY_TOPIC
        },
        {
            "topic": COVER_AVAILIBILITY_TOPIC
        }
    ],
    "availability_mode": "all",
    "device_class": "curtain",
    "command_topic": SET_COMMAND_TOPIC,
    "state_topic": STATE_TOPIC,
    "position_topic": POSITION_TOPIC,
    "set_position_topic": SET_POSITION_TOPIC,
    "device": MQTT_DEVICE,
    "json_attributes_topic":  ATTRIBUTES_TOPIC,
    "name": "Switch Bot Curtain",
    "optimistic": "false",
    "unique_id": f"{CLIENT_ID}_light_esp32"
}
MQTT_BATTERY_DISCOVERY_DATA = {
    "availability": [
        {
            "topic": ESP_AVAILIBILITY_TOPIC
        },
        {
            "topic": COVER_AVAILIBILITY_TOPIC
        }
    ],
    "availability_mode": "all",
    "device_class": "battery",
    "device": MQTT_DEVICE,
    "json_attributes_topic":  BATTERY_ATTRIBUTES_TOPIC,
    "state_topic": BATTERY_STATE_TOPIC,
    "name": "Switch Bot Curtain Battery",
    "optimistic": "false",
    "unique_id": f"{CLIENT_ID}_battery_esp32",
    "unit_of_measurement": "%"
}
MOTIONS = [
    "static",
    "closing",
    "opening",
]
STATES_OF_CHARGE = [
    "not_charging",
    "charging_by_adapter",
    "charging_by_solar",
    "adapter_fully_charged",
    "solar_fully_charged",
    "solar_not_charging",
    "charging_error",
]

FETCH_STATE_COMMAND = bytearray(b'\x57\x02')
FETCH_ADVANCED_PAGE_COMMAND = bytearray(b'\x57\x0F\x46\x04\x02')
STOP_STATE_COMMAND = bytearray(b'\x57\x0F\x45\x01\x00\xFF')
PERIODS_TO_WAIT_IN_STANDBY = 20
TIME_TO_WAIT_WHILE_MOVING = 1
ADDR_PUBLIC = 0
ADDR_RANDOM = 1
DATA_SERVICE = bluetooth.UUID("cba20d00-224d-11e6-9fb8-0002a5d5c51b")
NOTIFICATION_CHAR = bluetooth.UUID("cba20003-224d-11e6-9fb8-0002a5d5c51b")
WRITE_CHAR = bluetooth.UUID("cba20002-224d-11e6-9fb8-0002a5d5c51b")
