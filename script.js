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
    res = await deviceOperation("SimulatedDevice", true, "2000-01-01T00:00:00");
    if (res == false) {
      getDataFromEndpointAndSetHTML(deviceID)
      alert("Error with starting the device")
    }
  } else {
    res = await deviceOperation("SimulatedDevice", false, "2000-01-01T00:00:00");
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
    charging_status_text.textContent = "on";
  } else {
    charge_btn_1.textContent = START;
    charging_status_text.textContent = "off";
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

const selectHrs = document.getElementById("cb-schedule-select-hr")
const selectMinutes = document.getElementById("cb-schedule-select-minutes")
const selectInterval = document.getElementById("cb-schedule-select-interval")
const scheduleBtn = document.getElementById("cb-schedule-btn")
const scheduleDayText = document.getElementById("cb-schedule-day-text")

// Scheduling
const hrArr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
const minArr = ['00', '15', '30', '45']
const intervalArr = ['am', 'pm']

hrArr.forEach(h => {
  const optionH = new Option(h.toString(), h)
  selectHrs.add(optionH)
})
minArr.forEach(m => {
  const optionM = new Option(m.toString(), m)
  selectMinutes.add(optionM)
})

intervalArr.forEach(i => {
  const optionI = new Option(i.toString(), i)
  selectInterval.add(optionI)
})

const getTime = function () {
  const time = new Date()
  let hrs = time.getHours().toString()
  if (hrs.length == 1) {
    hrs = "0" + hrs;
  }
  let minutes = time.getMinutes().toString()
  if (minutes.length == 1) {
    minutes = "0" + minutes;
  }
  return [hrs,  minutes]
}

const convertToISOFormat = function (isTomorrow, hour, min) {
  const date = new Date()
  if (isTomorrow == true) {
    date.setDate(date.getDate() + 1)
  }
  let dateStr = date.getFullYear() + "-";
  dateStr += date.getMonth() <= 8 ? "0" + (date.getMonth() + 1) : (date.getMonth() + 1)
  dateStr += "-"
  dateStr += date.getDay() <= 9 ? "0" + date.getDate() : date.getDate()
  dateStr += 'T';
  dateStr += hour.toString() + ":" + min.toString() + ":00"
  return dateStr
}

const getScheduledSelectTime24HourClock = function () {
  const min = selectMinutes.value;
  const interval = selectInterval.value;
  let hr = selectHrs.value
  if (hr == '12' && interval == 'am') {
    hr = "00";
  } else if (hr.length == 1) {
    hr = "0" + hr;
  }
  if (hr != '12' && interval == 'pm') {
    hr = (parseInt(hr) + 12).toString()
  }
  return [hr, min, interval]
}

const isTommorrow = function () {
  const [hr, min] = getTime()
  let [sHr, sMin, _] = getScheduledSelectTime24HourClock()
  let isTomorrow = true;
  if (sHr > hr || (sHr == hr && sMin > min)) {
    isTomorrow = false;
  }
  return isTomorrow
}

const changeTodayTomorrowText = function (text) {
  scheduleDayText.textContent = text
}

selectHrs.addEventListener("change", () => {
  const tomorrow = isTommorrow()
  const text = tomorrow == true ? `Tomorrrow` : `Today`;
  changeTodayTomorrowText(text)
})

selectMinutes.addEventListener("change", () => {
  const tomorrow = isTommorrow()
  const text = tomorrow == true ? `Tomorrrow` : `Today`;
  changeTodayTomorrowText(text)
})

selectInterval.addEventListener("change", () => {
  const tomorrow = isTommorrow()
  const text = tomorrow == true ? `Tomorrrow` : `Today`;
  changeTodayTomorrowText(text)
})

scheduleBtn.addEventListener("click", async () => {
  const [hr, min, _] = getScheduledSelectTime24HourClock()
  const tomorrow = isTommorrow()
  const t = convertToISOFormat(tomorrow, hr, min)
  const res = await deviceOperation("SimulatedDevice", true, t);
  if (res == false) {
    getDataFromEndpointAndSetHTML("SimulatedDevice")
    alert("Error scheduling the device")
  }
})