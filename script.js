const charge_btn_1 = document.getElementById("cb-charge-btn");
const refresh_btn_1 = document.getElementById("cb-refresh-btn");
const name_text = document.getElementById("cb-name");
const battery_percentage_text = document.getElementById(
  "cb-battery-percentage",
);
const charging_status_text = document.getElementById("cb-charging-status");
const online_status_text = document.getElementById("cb-online-status");
const online_status_text_condition = document.getElementById("cb-online-status-condition");
const last_connectivity_text = document.getElementById("cb-last-connection");

let isCharging = false;
const START = "Start";
const STOP = "Stop";

const setHTMLDataElements = function (jsonData) {
  // Device name
  name_text.textContent = jsonData["deviceID"];

  // Battery percentage
  battery_percentage_text.textContent = jsonData["batteryPercentage"] + "%";

  // Charging Status
  charging_status_text.textContent = jsonData["charging"];
  isCharging = jsonData["charging"] == "on" ? true : false;
  handleCarChargingHTMLState(isCharging)

  // Online info
  online_status_text.textContent = jsonData["status"];
  online_status_text_condition.textContent = jsonData["status"] == "offline" ? "* required to start/stop charging" : "";
  const date = new Date(jsonData["lastConnectivity"]);
  last_connectivity_text.textContent = date.toString();
};

const getDataFromEndpoint = async function (deviceID) {
  const url = `https://kennys-function-app-for-task-hcg5fmbag3gqgnfe.australiaeast-01.azurewebsites.net/api/device/${deviceID}/status`;
  let js = null
  try {
    const res = await fetch(url, {
      method: "GET",
    });
    js = await res.json();
  } catch (err) {
    console.log(err.message);
  }
  return js;
};


const getDataFromEndpointAndSetHTML = async function (deviceID) {
  const jsonData = await getDataFromEndpoint(deviceID)
  if (jsonData != null) {
    setHTMLDataElements(jsonData)
  }
}

const deviceOperation = async function (deviceID, toCharge, isotime) {
  const url = `https://kennys-function-app-for-task-hcg5fmbag3gqgnfe.australiaeast-01.azurewebsites.net/api/device/${deviceID}`;
  const body = {
    toCharge: toCharge,
    time: isotime,
  };
  let resb = false;
  try {
    const res = await fetch(url, {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (res.status == 400 || res.status == 503) {
      resb = false;
    } else {
      resb = true;
    }
  } catch (err) {
    resb = false;
  }
  return resb;
};

const handleCarChargingFunction = async function (deviceID, toCharge) {
  let res = false;
  if (toCharge) {
    res = await deviceOperation("SimulatedDevice", true, "2024-04-04");
    if (res == false) {
      getDataFromEndpointAndSetHTML(deviceID)
      alert("Error with starting the device")
    }
  } else {
    res = await deviceOperation("SimulatedDevice", false, "2024-04-04");
    if (res == false) {
      getDataFromEndpointAndSetHTML(deviceID)
      alert("Error with stopping the device")
    }
  }
  return res;
};

const handleCarChargingHTMLState = function (nextState) {
  if (nextState) {
    charge_btn_1.textContent = STOP;
  } else {
    charge_btn_1.textContent = START;
  }
};

const onChargeButtonClick = async function (deviceID, toStartCharge) {
  const res = await handleCarChargingFunction(deviceID, toStartCharge);
  if (res == true) {
    handleCarChargingHTMLState(toStartCharge);
    isCharging = toStartCharge;
  } else {
    isCharging = false
    handleCarChargingHTMLState(isCharging)
    charge_btn_1.disabled = true;
  }
};

const onRefreshButtonClick = async function () {
   refresh_btn_1.textContent = "Refreshing...";
   refresh_btn_1.disabled = true;
   await getDataFromEndpointAndSetHTML("SimulatedDevice")
   refresh_btn_1.textContent = "Refresh";
   refresh_btn_1.disabled = false;
   if (online_status_text.textContent == "online") {
      charge_btn_1.disabled = false;
   } else {
    charge_btn_1.disabled = true;
   }
}

charge_btn_1.addEventListener("click", async () => {
  await onChargeButtonClick("SimulatedDevice", !isCharging);
});

refresh_btn_1.addEventListener("click", async () => {
  await onRefreshButtonClick()
})