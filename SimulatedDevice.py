from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import MethodResponse, MethodRequest

import os
import sys
import asyncio
from asyncio import Task, CancelledError, TimeoutError

from abc import abstractmethod
from typing import Callable
import json
from datetime import datetime

import click


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
            try:
                await asyncio.sleep(self.sleepSec)
                await self.callback(self.sleepSec)
            except CancelledError:
                return

    def stop(self):
        self.isRunning = False
    
class Device:

    class ScheduledTask:

        def __init__(self, scheduledTask : asyncio.Task, isoformat : str):
            self.scheduledTask = scheduledTask
            self.isoformat = isoformat
        
        def getScheduledTask(self) -> asyncio.Task:
            return self.scheduledTask
        
        def getIsoformat(self) -> str:
            return self.isoformat
        
    def __init__(self, name : str = 0, batteryPrct: int = 0, chargeRate : float = 1, isCharging : bool = False):
        self.name = name
        self.batteryPrct : float = batteryPrct
        self.isCharging : bool = isCharging
        self.chargeRate : float = chargeRate
        self.timer = Timer(name, 5, self.__defaultCallback)
        self.task = None
        self.scheduledTask = None
    
    async def __defaultCallback(self, timePassed):
        await self.templateUpdate(timePassed)

    # Template Method
    async def templateUpdate(self, timePassed):
        changedBP = self._update(timePassed)
        await self._hasUpdated(changedBP)

    def _setBatteryPercentage(self, bp : float):
        self.batteryPrct = bp

    @abstractmethod
    def _hasUpdated(self, timePassed):
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
        if (self.task == None or self.task.done() == True):
            self.isCharging = True
            self.task = asyncio.create_task(self.timer.start())
            await self._startHook()
        return True
    
    # Does not start scheduling when scheduled time in isoFormat < current time.
    async def scheduledStart(self, isoFormat : str, hook : bool = True) -> bool:
        async def _ss(seconds : int):
            try:
                await asyncio.sleep(seconds)
                await self.start()
            except CancelledError:
                return
        seconds = datetimeIsoformatDiffSeconds(datetime.now().isoformat(), isoFormat)
        if (seconds <= 0):
            return False
        if self.task != None:
            self.task.cancel()
        self.scheduledTask = self.ScheduledTask(asyncio.create_task(_ss(seconds)), isoFormat)
        if (hook):
            await self._scheduledStartHook(isoFormat)
        return True

    @abstractmethod
    async def _scheduledStartHook(self):
        pass

    @abstractmethod
    async def _startHook(self):
        pass

    async def stop(self) -> bool:
        self.isCharging = False
        if (self.task == None):
            return True

        res = False
        self.task.cancel()
        try:
            await asyncio.wait_for(self.task, timeout=4.0)
        except TimeoutError:
            res = True
        await self._stopHook()
        return res
    
    @abstractmethod
    async def _stopHook(self):
        pass

    def getName(self) -> str:
        return self.name
    
    def getBatteryPercentage(self) -> float:
        return self.batteryPrct
    
    def getChargingStatus(self) -> bool:
        return self.isCharging
    
    def getScheduledStartLocalTime(self) -> str:
        if (self.scheduledTask == None):
            return "None"
        nowdt = datetime.now()
        dt = datetime.fromisoformat(self.scheduledTask.getIsoformat())
        seconds = datetimeIsoformatDiffSeconds(nowdt.isoformat(), dt.isoformat())
        if (seconds < 0):
            return "None"
        return str(dt.date().strftime("%A %d %B %Y")) + " " + str(dt.time())[:-3]
        
    async def shutdown(self) -> bool:
        await self.shutdownHook()
        return True

    @abstractmethod
    async def shutdownHook(self) -> bool:
        pass
    
# Simulation of the Car Device
class SimulatedCarDeviceIOT(Device):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deviceClient = None

    def setDeviceClient(self, deviceClient : IoTHubDeviceClient):
        self.deviceClient = deviceClient

    async def __updateAdditionalProperties(self, client : IoTHubDeviceClient, reportedProperties : dict):
        await asyncio.create_task(client.patch_twin_reported_properties(reportedProperties))

    async def _hasUpdated(self, changedBP):
        # Additional Properties
        if (changedBP and self.isCharging):
            await asyncio.create_task(self.__updateAdditionalProperties(self.deviceClient, {"isCharging" : self.isCharging, "batteryPercentage" : self.batteryPrct}))
            await aQueue.put(("device_update_charge", self.batteryPrct))

    async def _startHook(self):
        await asyncio.create_task(self.__updateAdditionalProperties(self.deviceClient, {"isCharging" : self.isCharging, "batteryPercentage" : self.batteryPrct}))
        await aQueue.put(("device_update_charge", self.batteryPrct))

    async def _stopHook(self):
        await asyncio.create_task(self.__updateAdditionalProperties(self.deviceClient, {"isCharging" : self.isCharging, "batteryPercentage" : self.batteryPrct}))
        await aQueue.put(("device_update_main", self.batteryPrct))
    
    async def _scheduledStartHook(self, isoformat : str):
        await asyncio.create_task(self.__updateAdditionalProperties(self.deviceClient, {"scheduledStart" : isoformat}))
        await aQueue.put(("device_update_main", self.batteryPrct))

    async def shutdownHook(self) -> bool:
        await asyncio.create_task(self.__updateAdditionalProperties(self.deviceClient, {"isCharging" : False, "batteryPercentage" : self.batteryPrct}))
        await aQueue.put(("device_shutdown", "Shutdown"))
        
class CLI:

    def printMessage(self, name : str, batteryPercentage : float, chargeStatus : bool, scheduled : str = "None", messageType : str = "main"):
        if messageType == "main":
            print("======================================")
            print(f"{name}")
            print(f"Battery Percentage: {batteryPercentage}%")
            print(f"Charge Status: {'Charging' if chargeStatus else 'Not Charging'}")
            print()
            print(f"Scheduled: {scheduled}")
            print()
            print("Device Online")
            print("======================================")
        if messageType == "charge":
            print("======================================")
            print(f"{name}")
            print(f"Battery Percentage: {batteryPercentage}%")
            print(f"Charge Status: {'Charging' if chargeStatus else 'Not Charging'}")
            print("======================================")
        return
    
    def printShutdownMessage(self, name : str):
        print(f"{name} turned off")
    
# For seconds to be positive, iso2 > iso1
def datetimeIsoformatDiffSeconds(iso1 : str, iso2 : str):

    iso1d = datetime.fromisoformat(iso1)
    iso2d = datetime.fromisoformat(iso2)
    minutes = 0
    if (iso2d.day >= iso1d.day):
        minutes += (iso2d.day - iso1d.day) * 24 * 60
        
        minutes -= (iso1d.hour * 60)
        minutes -= iso1d.minute
        
        minutes += (iso2d.hour * 60)
        minutes += iso2d.minute
        
    seconds = minutes * 60
    seconds -= iso1d.second

    seconds -= iso1d.microsecond / 1e6
    return seconds

async def main(reset):

    # Device connection
    connection_string = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
    deviceClient = IoTHubDeviceClient.create_from_connection_string(connection_string)
    await deviceClient.connect()

    # Initialise object
    scd = SimulatedCarDeviceIOT(name = "SimulatedDevice", batteryPrct = 0, chargeRate = 0.1)
    scd.setDeviceClient(deviceClient)
    deviceTwin = await deviceClient.get_twin()
    
    # Handle cl args
    if reset == False:
        if "reported" in deviceTwin and "batteryPercentage" in deviceTwin["reported"]:
            scd._setBatteryPercentage(deviceTwin['reported']["batteryPercentage"])
    if "reported" in deviceTwin and "scheduledStart" in deviceTwin["reported"]:
        await scd.scheduledStart(deviceTwin["reported"]["scheduledStart"], hook=False)

    # Attach handler
    mainLoop = asyncio.get_running_loop()
    def assignDeviceMethodHandlerToMainLoop(method_request : MethodRequest):
        asyncio.run_coroutine_threadsafe(deviceMethodHandler(method_request), mainLoop)
        
    async def deviceMethodHandler(method_request : MethodRequest):
        message = "Recieved Message"
        try:
            payload_dict : dict[str,str] = method_request.payload
            if method_request.name == "handleChargingSwitch":
                if payload_dict["toCharge"] == True:
                    dateTimeNowIso = datetime.now().isoformat()
                    dateTimeSchIso = payload_dict["dateTime"]
                    if dateTimeSchIso <= dateTimeNowIso:
                        res = await scd.start()
                        message = "Started charging successfully"
                    else:
                        res = await scd.scheduledStart(dateTimeSchIso)
                        dt = datetime.fromisoformat(dateTimeSchIso)
                        message = f"Scheduled start at {dt.astimezone()} successfully"
                elif payload_dict["toCharge"] == False:
                    res = await scd.stop()
                    message = "Stopped charging successfully"
                    
            res_payload = {
                "message" : message
            }
            method_response = MethodResponse.create_from_method_request(method_request, 200, json.dumps(res_payload))
            await deviceClient.send_method_response(method_response)
        except Exception as e:
            method_response = MethodResponse.create_from_method_request(method_request, 400, json.dumps({"message" : "Internal Error"}))
            await deviceClient.send_method_response(method_response)
    deviceClient.on_method_request_received = assignDeviceMethodHandlerToMainLoop
    
    # Command line and events
    cli = CLI()
    async def dispatcher(aQueue : asyncio.Queue):
        while True:
            event, message = await aQueue.get()
            match event:
                case "device_update_main":
                        cli.printMessage(scd.getName(), scd.getBatteryPercentage(), scd.getChargingStatus(), scd.getScheduledStartLocalTime())
                case "device_update_charge":
                        cli.printMessage(scd.getName(), scd.getBatteryPercentage(), scd.getChargingStatus(), messageType="charge")
                case "device_shutdown":
                        cli.printShutdownMessage(scd.getName())

    asyncio.create_task(dispatcher(aQueue))
    cli.printMessage(scd.getName(), scd.getBatteryPercentage(), scd.getChargingStatus(), scd.getScheduledStartLocalTime())
    try:
        while True:
            await asyncio.sleep(1)
    except CancelledError:
        await scd.shutdown()
        await deviceClient.disconnect()
        try:
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for t in tasks:
                t.cancel()
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=4.0)
        except TimeoutError:
            sys.exit(0)
        sys.exit(0)

@click.command()
@click.option('--reset', '-r', default=False, help="Reset battery Percentage")
def execute(reset):
    asyncio.run(main(reset))

if __name__ == '__main__':
    execute()