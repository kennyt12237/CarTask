import os
import asyncio
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import MethodResponse, MethodRequest
from abc import abstractmethod
from typing import Callable
import json
import signal
import sys

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
        self.task = None

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

    async def start(self) -> bool:
        self.isCharging = True
        self.task = asyncio.create_task(self.timer.start())
        return True
    
    async def stop(self) -> bool:
        self.isCharging = False
        self.timer.stop()
        self.task.cancel()

        try:
            await self.task
        except asyncio.CancelledError:
            return True
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

    def printMessageAndWaitForInput(self, name : str, batteryPercentage : float, chargeStatus : bool):
        print("======================================")
        print(f"Car: {name}")
        print(f"Battery Percentage: {batteryPercentage}")
        print(f"Charge Status: {'Charging' if chargeStatus else 'Not Charging'}")
        print()
        print("Device Online")
        print("======================================")
        return

async def main():
    scd = SimulatedCarDeviceIOT(name = "SimulatedDevice", batteryPrct = 0, chargeRate = 0.1)
    symKey = os.getenv("IOTHUB_SYMMETRIC_KEY")
    hostname = "Kenny-IoT-Hub-For-Task.azure-devices.net"
    device = "SimulatedDevice"
    deviceClient = IoTHubDeviceClient.create_from_symmetric_key(symKey,hostname, device)
    scd.setDeviceClient(deviceClient)
    cli = CLI()
    await deviceClient.connect()

    async def device_method_handler(method_request : MethodRequest):
        payload_dict : dict[str,str] = method_request.payload
        if method_request.name == "handleChargingSwitch":
            if payload_dict["toCharge"] == True:
                res = await scd.start()
            elif payload_dict["toCharge"] == False:
                res = await scd.stop()
        res_payload = {
            "message" : "Received Message"
        }
        method_response = MethodResponse.create_from_method_request(method_request, 200, json.dumps(res_payload))
        await deviceClient.send_method_response(method_response)
    
    deviceClient.on_method_request_received = device_method_handler
    async def dispatcher(aQueue : asyncio.Queue):
        while True:
            event, message = await aQueue.get()
            match event:
                case "device_update":
                        cli.printMessageAndWaitForInput(scd.getName(), scd.getBatteryPercentage(), scd.getChargingStatus())
    cli.printMessageAndWaitForInput(scd.getName(), scd.getBatteryPercentage(), scd.getChargingStatus())
    dispatcher_task = asyncio.create_task(dispatcher(aQueue))

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        # dispatcher_task.cancel()
        # await dispatcher_task
        await deviceClient.shutdown()
        print("=========Completed========") 
        sys.exit(0)


asyncio.run(main())