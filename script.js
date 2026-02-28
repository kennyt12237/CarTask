const charge_btn_1 = document.getElementById("cb-charge-btn-1");
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
  name_text.textContent = jsonData["deviceID"];
  battery_percentage_text.textContent = jsonData["batteryPercentage"] + "%";
  charging_status_text.textContent = jsonData["charging"];
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

const handleCarChargingFunction = function (toCharge) {
  // (TODO) Send to API call for both conditions
  if (toCharge) {
    alert("Charging...");
  } else {
    alert("Chargin Stopped.");
  }
  return toCharge;
};

const handleCarChargingHTMLState = function (nextState) {
  if (nextState) {
    charge_btn_1.textContent = STOP;
  } else {
    charge_btn_1.textContent = START;
  }
};

const onChargeButtonClick = function (toStartCharge) {
  handleCarChargingFunction(toStartCharge);
  handleCarChargingHTMLState(toStartCharge);
  isCharging = toStartCharge;
  //   console.log("IsCharging:", isCharging);
};

document;
charge_btn_1.addEventListener("click", () => {
  onChargeButtonClick(!isCharging);
});

console.log(getDataFromEndpoint("SimulatedDevice"));
