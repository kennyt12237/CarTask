import azure.functions as func
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.protocol.models import CloudToDeviceMethod, CloudToDeviceMethodResult
from msrest.exceptions import HttpOperationError
import logging
import os 
import json
import datetime

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
connectionString = os.getenv("SERVICE_CONNECTION_STRING")
registryManager = IoTHubRegistryManager(connectionString)


@app.route(route="device/{deviceID}/status", auth_level=func.AuthLevel.ANONYMOUS, methods=["get"])
def getDeviceStatus(req: func.HttpRequest) -> func.HttpResponse:
    deviceId = req.route_params.get("deviceID")
    json_data = {
        "deviceID" : deviceId,
        "status" : "null",
        "charging" : "False",
        "batteryPercentage" : 0,
        "lastConnectivity" : "null",
        "error" : {
            "code" : "null",
            "message" : "null"
        }
    }
    try:
        twin = registryManager.get_twin(deviceId)
    except HttpOperationError as e:
        json_data["error"] = {
            "code" : "DEVICE_NOT_FOUND",
            "message" : e.message
        }
        return func.HttpResponse(json.dumps(json_data), status_code=503)
    json_data["status"] = "online" if twin.connection_state.lower() == "connected" else "offline",
    json_data["lastConnectivity"] = twin.last_activity_time.isoformat(),
    return func.HttpResponse(json.dumps(json_data), status_code=200)
    
@app.route(route="device/{deviceID}", auth_level=func.AuthLevel.ANONYMOUS, methods=["post"])
def chargeDevice(req: func.HttpRequest) -> func.HttpResponse:
    toCharge = None
    time = None
    try:
        req_body = req.get_json()
    except ValueError:
        pass
    else:
        toCharge = req_body.get('toCharge')
        time = req_body.get('time')

    if toCharge != None and time != None:
        payload = {"command" : "chargeOperation",
                   "toCharge" : toCharge,
                   "dateTime" : time,
                   "response_timeout_in_seconds" : 20,
                   "connect_timeout_in_seconds" : 0}
        method = CloudToDeviceMethod(method_name="handleChargingSwitch", payload=payload)
        try:
            res : CloudToDeviceMethodResult = registryManager.invoke_device_method(device_id="SimulatedDevice", direct_method_request=method)
            json_payload = json.loads(res.payload)
            return func.HttpResponse(json_payload["message"], status_code=res.status)
        except HttpOperationError as e:
            return func.HttpResponse(e.message, status_code=503)
    return func.HttpResponse(
        "This HTTP triggered function executed unsuccessfully.",
        status_code=400
    )