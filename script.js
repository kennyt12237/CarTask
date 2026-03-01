const charge_btn_1 = document.getElementById("cb-charge-btn");
const refresh_btn_1 = document.getElementById("cb-refresh-btn");
const name_text = document.getElementById("cb-name");
const battery_percentage_text = document.getElementById(
  "cb-battery-percentage",
);
const charging_status_text = document.getElementById("cb-charging-status");
const online_status_text = document.getElementById("cb-online-status");
const last_connectivity_text = document.getElementById("cb-last-connection");

let isCharging = false;
const START = "Start";
const STOP = "Stop";

const setHTMLDataElements = function (jsonData) {
  console.log(jsonData)
  name_text.textContent = jsonData["deviceID"];
  battery_percentage_text.textContent = jsonData["batteryPercentage"] + "%";
  charging_status_text.textContent = jsonData["charging"] == "False" ? "Off" : "On";
  online_status_text.textContent = jsonData["status"];
  const date = new Date(jsonData["lastConnectivity"]);
  last_connectivity_text.textContent = date.toString();
};
const getDataFromEndpoint = async function (deviceID) {
  const url = `https://kennys-function-app-for-task-hcg5fmbag3gqgnfe.australiaeast-01.azurewebsites.net/api/device/${deviceID}/status`;
  try {
    const res = await fetch(url, {
      method: "GET",
    });
    const js = await res.json();
    setHTMLDataElements(js);
  } catch (err) {
    console.log(err.message);
  }
  return;
};

const deviceOperation = async function (deviceID, toCharge, isotime) {
  const url = `https://kennys-function-app-for-task-hcg5fmbag3gqgnfe.australiaeast-01.azurewebsites.net/api/device/${deviceID}`;
  const body = {
    toCharge: toCharge,
    time: isotime,
  };
  try {
    const res = await fetch(url, {
      method: "POST",
      body: JSON.stringify(body),
    });
    console.log(res)
  } catch (err) {
    console.log(err.message);
    return false;
  }
  return true;
};
const handleCarChargingFunction = async function (toCharge) {
  var res;
  if (toCharge) {
    res = await deviceOperation("SimulatedDevice", true, "2024-04-04");
    if (res == false) {
      alert("Error with starting the device")
    }
  } else {
    res = await deviceOperation("SimulatedDevice", false, "2024-04-04");
    if (res == false) {
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

const onChargeButtonClick = async function (toStartCharge) {
  const res = await handleCarChargingFunction(toStartCharge);
  if (res == true) {
    handleCarChargingHTMLState(toStartCharge);
    isCharging = toStartCharge;
  }
};

const onRefreshButtonClick = async function () {
   await getDataFromEndpoint("SimulatedDevice")
}

charge_btn_1.addEventListener("click", async () => {
  await onChargeButtonClick(!isCharging);
});

refresh_btn_1.addEventListener("click", async () => {
  await onRefreshButtonClick()
})