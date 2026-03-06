import os
import asyncio
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import MethodResponse, MethodRequest
from abc import abstractmethod
from typing import Callable
import json
import sys
import click
from datetime import datetime

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
        changedBP = self._update(timePassed)
        await self.hasUpdated(changedBP)

    def _setBatteryPercentage(self, bp : float):
        self.batteryPrct = bp

    @abstractmethod
    def hasUpdated(self, timePassed):
        pass

    # Default linear charge rate
    def _update(self, timePassed) -> float:
        changedBP = False
        if (self.batteryPrct < 100):
            nextPercentage = self.batteryPrct + (timePassed * self.chargeRate)
            self.batteryPrct = min(100, nextPercentage)
            changedBP = True 
        return changedBP

    async def start(self) -> bool:
        self.isCharging = True
        self.task = asyncio.create_task(self.timer.start())
        await self.startHook()
        return True
    
    # Does not start scheduling when scheduled time in isoFormat < current time.
    async def scheduledStart(self, isoFormat : str) -> bool:
        async def _ss(seconds : int):
            await asyncio.sleep(seconds)
            await self.start()
        seconds = datetimeIsoformatDiffSeconds(datetime.now().isoformat(), isoFormat)
        if (seconds <= 0):
            return False
        asyncio.create_task(_ss(seconds))
        await self.scheduledStartHook(isoFormat)

    @abstractmethod
    async def scheduledStartHook(self):
        pass

    @abstractmethod
    async def startHook(self):
        pass

    async def stop(self) -> bool:
        self.isCharging = False
        self.timer.stop()
        self.task.cancel()

        res = False
        try:
            await self.task
        except asyncio.CancelledError:
            res = True
        await self.stopHook()
        return res
    
    @abstractmethod
    async def stopHook(self):
        pass

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

    async def __updateAdditionalProperties(self, client : IoTHubDeviceClient, reportedProperties : dict):
        await asyncio.create_task(client.patch_twin_reported_properties(reportedProperties))

    async def hasUpdated(self, changedBP):
        # Additional Properties
        if (changedBP and self.isCharging):
            await asyncio.create_task(self.__updateAdditionalProperties(self.deviceClient, {"isCharging" : self.isCharging, "batteryPercentage" : self.batteryPrct}))
            await aQueue.put(("device_update", self.batteryPrct))

    async def startHook(self):
        await asyncio.create_task(self.__updateAdditionalProperties(self.deviceClient, {"isCharging" : self.isCharging, "batteryPercentage" : self.batteryPrct}))
        await aQueue.put(("device_update", self.batteryPrct))

    async def stopHook(self):
        await asyncio.create_task(self.__updateAdditionalProperties(self.deviceClient, {"isCharging" : self.isCharging, "batteryPercentage" : self.batteryPrct}))
        await aQueue.put(("device_update", self.batteryPrct))
    
    async def scheduledStartHook(self, isoformat : str):
        await asyncio.create_task(self.__updateAdditionalProperties(self.deviceClient, {"scheduledStart" : isoformat}))

class CLI:

    def printMessageAndWaitForInput(self, name : str, batteryPercentage : float, chargeStatus : bool):
        print("======================================")
        print(f"Car: {name}")
        print(f"Battery Percentage: {batteryPercentage}%")
        print(f"Charge Status: {'Charging' if chargeStatus else 'Not Charging'}")
        print()
        print("Device Online")
        print("======================================")
        return

# Must be less than a day, iso2 > iso1
def datetimeIsoformatDiffSeconds(iso1 : str, iso2 : str):

    iso1d = datetime.fromisoformat(iso1)
    iso2d = datetime.fromisoformat(iso2)
    minutes = 0
    if (iso2d.day > iso1d.day):
        minutes += (24 - iso1d.hour) * 60
        minutes -= iso1d.minute
        minutes += (iso2d.hour * 60) + iso2d.minute
    else:
        minutes += (iso2d.hour - iso1d.hour) * 60
        minutes = (minutes + (iso2d.minute - iso1d.minute)) if iso2d.minute > iso1d.minute else (minutes - (iso1d.minute - iso2d.minute))
    return minutes * 60

async def main(reset):

    connection_string = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
    deviceClient = IoTHubDeviceClient.create_from_connection_string(connection_string)
    await deviceClient.connect()

    scd = SimulatedCarDeviceIOT(name = "SimulatedDevice", batteryPrct = 0, chargeRate = 0.1)
    scd.setDeviceClient(deviceClient)
    deviceTwin = await deviceClient.get_twin()
    if reset == False:
        if "reported" in deviceTwin and "batteryPercentage" in deviceTwin["reported"]:
            scd._setBatteryPercentage(deviceTwin['reported']["batteryPercentage"])
    if "reported" in deviceTwin and "scheduledStart" in deviceTwin["reported"]:
        await scd.scheduledStart(deviceTwin["reported"]["scheduledStart"])

    cli = CLI()
    async def device_method_handler(method_request : MethodRequest):
        payload_dict : dict[str,str] = method_request.payload
        if method_request.name == "handleChargingSwitch":
            if payload_dict["toCharge"] == True:
                dateTimeNowIso = datetime.now().isoformat()
                dateTimeSchIso = payload_dict["dateTime"]
                if dateTimeSchIso <= dateTimeNowIso:
                    res = await scd.start()
                else:
                    res = await scd.scheduledStart(dateTimeSchIso)
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

@click.command()
@click.option('--reset', '-r', default=False, help="Reset battery Percentage")
def execute(reset):
    asyncio.run(main(reset))

if __name__ == '__main__':
    execute()