const charge_btn_1 = document.getElementById("cb-charge-btn-1");
let isCharging = false;
const START = "Start";
const STOP = "Stop";

const getDataFromEndpoint = async function (deviceId) {
  const url = `https://kennys-function-app-for-task-hcg5fmbag3gqgnfe.australiaeast-01.azurewebsites.net/api/device/status/${deviceId}`
  console.log(url)
  try {
      await fetch(url, {
        method : "POST"
      }).then(res => console.log(res.json()));
  } catch (err) {
    console.log(err.message)
  }
  console.log("Finished")
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

console.log(getDataFromEndpoint("SimulatedDevice"))