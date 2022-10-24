import ulogging
import uasyncio as asyncio
import aioble
from random import randrange

CURTAIN_MAC = "F5:56:2C:90:CB:50"

log = ulogging.getLogger(__name__)
log.setLevel(ulogging.DEBUG)


async def main():
    device = aioble.Device(ADDR_RANDOM, CURTAIN_MAC)
    try:
        log.info("Connecting to %s", device)
        connection = await device.connect(timeout_ms=30000)
    except asyncio.TimeoutError:
        log.warning("Timeout during connection")
        return

    try:
        service = await connection.service(DATA_SERVICE)
        log.debug("Service: %s", service)
        write_characteristic = await service.characteristic(WRITE_CHAR)
        log.debug("Write Char: %s", write_characteristic)
        notification_characteristic = await service.characteristic(NOTIFICATION_CHAR)
        log.debug("Notification Char: %s", notification_characteristic)
        await notification_characteristic.subscribe(notify=True)

        async def on_notified():
            while True:
                notification = await notification_characteristic.notified()
                log.debug("notification %s", notification)
                if f"{notification}".startswith("b'\\x019,"):
                    log.debug("map: %s", _result_to_map(notification))

        async def fetchData():
            while True:
                await write_characteristic.write(bytearray(b'\x57\x02'))
                log.info("Sent fetch data message")
                await asyncio.sleep(10)

        async def moveToRandomSpot():
            while True:
                value = randrange(100)
                log.info("Moving to %s", value)
                await write_characteristic.write(new_pos_command(value))
                await asyncio.sleep(30)

        asyncio.get_event_loop().create_task(on_notified())
        asyncio.get_event_loop().create_task(fetchData())
        # asyncio.get_event_loop().create_task(moveToRandomSpot())
    except asyncio.TimeoutError:
        print("Timeout discovering services/characteristics")
        return

loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
