# Car Charge 
A Car charging webapp providing car information and car charging capabilities, with car being simulated and implemented using Python CLI, connected over Azure. 


The following entities are involved:
- WebApp: displays information about the simulated car with start and stop charging functions.
- Azure Functions: A backend receiving HTTP requests and communicating with the Azure IoTHub.
- IoTHub: A hub for Internet of Things (IoT) connecting devices.
- SimulatedDevice: A simulated car CLI.


![Image of entities and interaction](./images/Diagram.png)


## WebApp Requests
The user pressing the start charging button shows one of the flow from the WebApp to the SimulatedDevice. 


![Image of Start/Stop charging flow](./images/ChargeRequestFlow.png)
