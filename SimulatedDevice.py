import os
import asyncio
from azure.iot.device.aio import IoTHubDeviceClient
from abc import abstractmethod
from typing import Callable

aQueue = asyncio.Queue()

class Timer:

    def __init__(self, name : str, seconds : int, callback : Callable):
        super().__init__()
        self.name = name
        self.sleepSec = seconds
        self.isRunning = False
        self.callback = callback

    async def start(self):
        self.isRunning = True
        while (self.isRunning):
            await asyncio.sleep(self.sleepSec)
            await self.callback(self.sleepSec)

    def stop(self):
        self.isRunning = False
    
class Device:
    def __init__(self, name : str = 0, batteryPrct: int = 0, chargeRate : float = 1, isCharging : bool = False):
        self.name = name
        self.batteryPrct : float = batteryPrct
        self.isCharging : bool = isCharging
        self.chargeRate : float = chargeRate
        self.timer = Timer(name, 5, self.__defaultCallback)

    async def __defaultCallback(self, timePassed):
        await self.templateUpdate(timePassed)

    # Template Method
    async def templateUpdate(self, timePassed):
        self._update(timePassed)
        await self.hasUpdated(timePassed)

    @abstractmethod
    def hasUpdated(self, timePassed):
        pass

    # Default linear charge rate
    def _update(self, timePassed) -> float:
        self.batteryPrct = self.batteryPrct + timePassed * self.chargeRate
        return self.batteryPrct

    def start(self) -> bool:
        self.isCharging = True
        asyncio.create_task(self.timer.start())
        return True
    
    def stop(self) -> bool:
        self.isCharging = False
        self.timer.stop()
        return False

    def getName(self) -> str:
        return self.name
    
    def getBatteryPercentage(self) -> float:
        return self.batteryPrct
    
    def getChargingStatus(self) -> bool:
        return self.isCharging

# Simulation of the Car Device
class SimulatedCarDeviceIOT(Device):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deviceClient = None

    def setDeviceClient(self, deviceClient : IoTHubDeviceClient):
        self.deviceClient = deviceClient

    async def hasUpdated(self, timePassed):
        async def sendMessageAsync(client : IoTHubDeviceClient, msg : str):
            await client.send_message(msg)
        await asyncio.create_task(sendMessageAsync(self.deviceClient, self.batteryPrct))
        await aQueue.put(("device_update", self.batteryPrct))
        
class CLI:

    async def printMessageAndWaitForInput(self, name : str, batteryPercentage : float, chargeStatus : bool):
        print("======================================")
        print(f"Car: {name}")
        print(f"Battery Percentage: {batteryPercentage}")
        print(f"Charge Status: {'Charging' if chargeStatus else 'Not Charging'}")
        print("======================================")
        print()
        print("Options: Charge/Uncharge/Shutdown")
        res = await asyncio.to_thread(input, "Enter Input: ")
        await aQueue.put(("user_input", res))
        return

async def main():
    scd = SimulatedCarDeviceIOT(name = "DRC Car", batteryPrct = 0, chargeRate = 0.1)
    symKey = os.getenv("IOTHUB_SYMMETRIC_KEY")
    hostname = "Kenny-IoT-Hub-For-Task.azure-devices.net"
    device = "SimulatedDevice"
    deviceClient = IoTHubDeviceClient.create_from_symmetric_key(symKey,hostname, device)
    scd.setDeviceClient(deviceClient)
    cli = CLI()
    await deviceClient.connect()
    async def dispatcher(aQueue : asyncio.Queue):
        while True:
            event, message = await aQueue.get()
            print(f"Event: {event}, Message: {message}")
            match event:
                case "user_input":
                    match message:
                        case "Charge":
                            scd.start()
                            asyncio.create_task(cli.printMessageAndWaitForInput(scd.getName(), scd.getBatteryPercentage(), scd.getChargingStatus()))
                        case "Uncharge":
                            scd.stop()
                            asyncio.create_task(cli.printMessageAndWaitForInput(scd.getName(), scd.getBatteryPercentage(), scd.getChargingStatus()))
                        case "Shutdown":
                            break
                case "device_update":
                        asyncio.create_task(cli.printMessageAndWaitForInput(scd.getName(), scd.getBatteryPercentage(), scd.getChargingStatus()))
    asyncio.create_task(cli.printMessageAndWaitForInput(scd.getName(), scd.getBatteryPercentage(), scd.getChargingStatus()))
    await asyncio.gather(dispatcher(aQueue))
    await  deviceClient.shutdown()
    print("=========Completed========")

asyncio.run(main())

# def main():
#     scd = SimulatedCarDevice("Car1", 0, False, 0.1)
#     scd.start()
#     time.sleep(10)
#     scd.stop()
#     time.sleep(10)
# main()
# async def main():
#     aQueue = asyncio.Queue()
#     async def dispatcherLoop():
#         while True:
#             eventType, data = await aQueue.get()
#             print(f"Got event: {eventType} and data {data}")

#     async def timer(seconds):
#         await asyncio.sleep(seconds)
#         await aQueue.put(("timer", f"{seconds} have passed"))

#     async def cliLoop():
#         while True:
#             res = await asyncio.to_thread(input, "Enter your input: ")
#             print(f"You wrote {res}")
#             await aQueue.put(("user_input", res))
#             asyncio.create_task(timer(5))



#     await asyncio.gather(dispatcherLoop(), cliLoop())

# asyncio.run(main())