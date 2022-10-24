import aioble
import uasyncio as asyncio
import ulogging

import constants
import slutils

log = ulogging.getLogger(__name__)
log.setLevel(ulogging.DEBUG)


class BluetoothCover:
    STATE_2_NAMES = [
        ("is_solar_panel_connected", lambda bitStr: bitStr[0] == "1"),
        ("is_calibrated", lambda bitStr: bitStr[1] == "1"),
        ("motion_status",
         lambda bitStr: constants.MOTIONS[int(bitStr[2:4], 2)]),
    ]
    NAMES = [
        ("response_status", lambda byte_list: byte_list[0]),
        ("battery_percentage", lambda byte_list: byte_list[1]),
        ("firmware_version", lambda byte_list: byte_list[2]),
        ("device_chain_length", lambda byte_list: byte_list[3]),
        ("state_1", lambda byte_list: byte_list[4]),
        ("state_2", lambda byte_list: BluetoothCover._names_to_map(
            BluetoothCover.STATE_2_NAMES, BluetoothCover._byte_to_bin_str(byte_list[5]))),
        ("position", lambda byte_list: byte_list[6]),
        ("number_of_timers", lambda byte_list: byte_list[7]),
    ]
    ADV_NAMES = [
        ("response_status", lambda byte_list: byte_list[0]),
        ("battery_percentage", lambda byte_list: byte_list[1]),
        ("firmware_version", lambda byte_list: byte_list[2]),
        ("state_of_charge",
         lambda byte_list: constants.STATES_OF_CHARGE[int(byte_list[3])]),
    ]

    def __init__(self, mac, on_state_updated_callback, on_last_command_successfull_callback, is_inverted=False):
        self._on_state_updated_callback = on_state_updated_callback
        self._on_last_command_successfull_callback = on_last_command_successfull_callback
        self._device = aioble.Device(constants.ADDR_RANDOM, mac)
        self._write_characteristic = None
        self._notification_characteristic = None
        self._connection = None
        self._state = None
        self._adv_state = None
        self._is_inverted = is_inverted
        self._is_moving = False
        self._just_started_moving = False

    async def init(self):
        await self.connect()
        await self.start_listening()

    async def connect(self):
        is_connected = False
        self._on_last_command_successfull_callback(False)
        while not is_connected:
            try:
                self._connection = await self._device.connect(timeout_ms=30000)
                service = await self._connection.service(constants.DATA_SERVICE)
                log.debug("Service: %s", service)
                self._write_characteristic = await service.characteristic(constants.WRITE_CHAR)
                log.debug("Write Char: %s", self._write_characteristic)
                self._notification_characteristic = await service.characteristic(constants.NOTIFICATION_CHAR)
                log.debug("Notification Char: %s",
                          self._notification_characteristic)
                await self._notification_characteristic.subscribe(notify=True)
                is_connected = True
                self._on_last_command_successfull_callback(True)
            except (OSError, AttributeError) as e:  # type: ignore
                log.exc(e, "failed to connect")
                self._on_last_command_successfull_callback(False)
                await asyncio.sleep(1)

    async def start_listening(self):
        async def _listen_for_notifications():
            while True:
                try:
                    if self._notification_characteristic:
                        notification = await self._notification_characteristic.notified()
                        log.debug("notification %s", notification)
                        output = ""
                        for abyte in notification:
                            hexvalue = f"{abyte:x}"
                            hexvalue = f"{hexvalue:0>2}-"
                            output += hexvalue
                        log.debug("notification %s", output[:-1])
                        self._on_notification(notification)
                        if self._just_started_moving:
                            self._just_started_moving = False
                        self._on_last_command_successfull_callback(True)
                    else:
                        await asyncio.sleep(1)
                except aioble.DeviceDisconnectedError as e:  # type: ignore
                    log.exc(e, "Disconnected")
                    await self.connect()
                except (Exception, OSError) as e:  # type: ignore
                    log.exc(e, "Listening failed")
                    self._on_last_command_successfull_callback(False)
                except:  # pylint: disable=bare-except
                    log.error("Listening failed")
                    self._on_last_command_successfull_callback(False)

        asyncio.get_event_loop().create_task(_listen_for_notifications())

        async def _send_fetch_state():
            counter = constants.PERIODS_TO_WAIT_IN_STANDBY
            while True:
                if self._is_moving or counter == constants.PERIODS_TO_WAIT_IN_STANDBY:
                    await self._fetch_state()
                    counter = -1
                counter += 1
                await asyncio.sleep(constants.TIME_TO_WAIT_WHILE_MOVING)

        asyncio.get_event_loop().create_task(_send_fetch_state())

        async def _send_adv_fetch_state():
            await asyncio.sleep(constants.PERIODS_TO_WAIT_IN_STANDBY / 2)
            while True:
                await self._send_command(constants.FETCH_ADVANCED_PAGE_COMMAND)
                await asyncio.sleep(constants.PERIODS_TO_WAIT_IN_STANDBY)

        asyncio.get_event_loop().create_task(_send_adv_fetch_state())

    async def disconnect(self):
        if self._connection:
            self._connection.disconnect()

    async def move_to(self, pos):
        pos = self._invert_if_needed(pos)
        log.debug("Moving curtain to %s", pos)
        await self._send_command(self._new_pos_command(self._invert_if_needed(pos)))
        self._is_moving = True
        self._just_started_moving = True

    async def close(self):
        await self.move_to(self._invert_if_needed(0))

    async def open(self):
        await self.move_to(self._invert_if_needed(100))

    async def stop(self):
        await self._send_command(constants.STOP_STATE_COMMAND)

    @property
    def state(self):
        if self.has_state:
            flattened = slutils.flatten_dict(self._state)
            flattened["position"] = self.position
            flattened["state_2.motion_status"] = self._invert_motions_if_needed(
                flattened["state_2.motion_status"])
            return flattened
        return None

    @property
    def adv_state(self):
        if self.has_adv_state:
            flattened = slutils.flatten_dict(self._adv_state)
            flattened["is_adapter_connect"] = self.is_adapter_plugged_in
            return flattened
        return None

    @property
    def position(self):
        return self._invert_if_needed(self._get_result_or_default("position", None))

    @property
    def is_closed(self):
        return self.position < 5

    @property
    def motion_status(self):
        if self.state:
            if "state_2.motion_status" in self.state:
                motion_status = self.state["state_2.motion_status"]
                if motion_status == "static":
                    return "closed" if self.is_closed else "open"
                return motion_status
        return None

    @property
    def battery(self):
        if self.has_adv_state:
            if "battery_percentage" in self._adv_state:
                battery_percentage = self._adv_state["battery_percentage"]
                return battery_percentage
        return None

    @property
    def is_adapter_plugged_in(self):
        if self.has_adv_state:
            if "state_of_charge" in self._adv_state:
                state_of_charge = self._adv_state["state_of_charge"]
                return "adapter" in state_of_charge
        return None

    @property
    def has_state(self):
        return self._state is not None

    @property
    def has_adv_state(self):
        return self._adv_state is not None

    async def _send_command(self, command):
        try:
            if self._write_characteristic:
                await self._write_characteristic.write(command)
                log.debug("Sent command: %s", command)
                self._on_last_command_successfull_callback(True)
        except TypeError as e:
            log.exc(e, "Send command failed: %s", command)
            await self.connect()
        except (Exception, OSError) as e:  # type: ignore
            log.exc(e, "Send command failed: %s", command)
            self._on_last_command_successfull_callback(False)
        except:  # pylint: disable=bare-except
            log.error("Send command failed: %s", command)
            self._on_last_command_successfull_callback(False)

    def _on_notification(self, notification):
        if ",\\" in f"{notification}":
            notification = self._pad_bytes(bytearray(notification))
            if "x\\" in f"{notification}":
                self._state = BluetoothCover._names_to_map(
                    BluetoothCover.NAMES, notification)
                if not self._just_started_moving and self._state["state_2"]["motion_status"] == "static":
                    self._is_moving = False
                log.debug("State: %s", self._state)
            else:
                self._adv_state = BluetoothCover._names_to_map(
                    BluetoothCover.ADV_NAMES, notification)
                log.debug("ADV State: %s", self._adv_state)
            self._on_state_updated_callback(self)

    def _pad_bytes(self, abytes):
        bytes_to_add = 8 - len(abytes)
        for _ in range(bytes_to_add):
            abytes.append(0)
        return abytes

    async def _fetch_state(self):
        await self._send_command(constants.FETCH_STATE_COMMAND)

    def _get_result_or_default(self, result_name, default):
        if self.has_state:
            if result_name in self._state:
                return self._state[result_name]
        return default

    def _new_pos_command(self, pos):
        data = bytearray(b'\x57\x0F\x45\x01\x05\xFF')
        data.append(pos)
        return data

    @staticmethod
    def _byte_to_bin_str(byte):
        bin_value = f"{byte:b}"
        bin_value = f"{bin_value:0>4}"
        return bin_value

    @staticmethod
    def _names_to_map(names, value):
        result = {}
        for name in names:
            result[name[0]] = name[1](value)
        return result

    def _invert_if_needed(self, position):
        if self._is_inverted and position is not None:
            return 100 - position
        return position

    def _invert_motions_if_needed(self, motion):
        if self._is_inverted:
            if motion == "closing":
                return "opening"
            if motion == "opening":
                return "closing"
        return motion
