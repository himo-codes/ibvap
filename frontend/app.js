const API_BASE_URL = "http://localhost:8000";
const POLL_INTERVAL_MS = 2500;
const STATS_POLL_INTERVAL_MS = 1500;
const ALARM_EVENT_TYPES = new Set([
  "VIRTUAL_FENCE_CROSS",
  "RESTRICTED_ZONE_ENTRY",
]);

const feed = document.querySelector("#alert-feed");
const emptyState = document.querySelector("#empty-state");
const connectionStatus = document.querySelector("#connection-status");
const alertCount = document.querySelector("#alert-count");
const cameraToggle = document.querySelector("#camera-toggle");
const cameraPanel = document.querySelector("#camera-panel");
const cameraFeed = document.querySelector("#camera-feed");
const alarmBanner = document.querySelector("#alarm-banner");
const personCount = document.querySelector("#person-count");
const vehicleCount = document.querySelector("#vehicle-count");
const animalCount = document.querySelector("#animal-count");
const renderedEvents = new Map();
let initialPollComplete = false;
let audioContext;

window.addEventListener("DOMContentLoaded", () => {
  cameraToggle.addEventListener("click", toggleCamera);
  document.addEventListener("pointerdown", unlockAudio, { once: true });
  pollEvents();
  pollStats();
  setInterval(pollEvents, POLL_INTERVAL_MS);
  setInterval(pollStats, STATS_POLL_INTERVAL_MS);
});

async function pollEvents() {
  try {
    const response = await fetch(`${API_BASE_URL}/events`);
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const events = await response.json();
    connectionStatus.textContent = `Live - refreshed ${new Date().toLocaleTimeString()}`;
    renderNewEvents(events, initialPollComplete);
    initialPollComplete = true;
    updateSummary();
  } catch (error) {
    connectionStatus.textContent = `Backend unavailable: ${error.message}`;
  }
}

async function pollStats() {
  try {
    const response = await fetch(`${API_BASE_URL}/stats`);
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const stats = await response.json();
    personCount.textContent = String(stats.person || 0);
    vehicleCount.textContent = String(stats.vehicle || 0);
    animalCount.textContent = String(stats.animal || 0);
  } catch (error) {
    personCount.textContent = "-";
    vehicleCount.textContent = "-";
    animalCount.textContent = "-";
  }
}

function renderNewEvents(events, shouldAlarm) {
  for (const event of [...events].reverse()) {
    const existing = renderedEvents.get(event.event_id);
    if (existing) {
      syncAckState(existing, event);
      continue;
    }

    const element = createAlertElement(event);
    renderedEvents.set(event.event_id, element);
    feed.prepend(element);
    if (shouldAlarm && ALARM_EVENT_TYPES.has(event.event_type)) {
      triggerAlarm();
    }
  }
}

function createAlertElement(event) {
  const article = document.createElement("article");
  article.className = `alert severity-${severityClass(event.event_type)}`;
  article.dataset.eventId = event.event_id;
  article.dataset.ackStatus = event.ack_status || "pending";

  const body = document.createElement("div");
  body.className = "alert-body";

  const heading = document.createElement("div");
  heading.className = "alert-heading";

  const eventType = document.createElement("span");
  eventType.className = "event-type";
  eventType.textContent = event.event_type;

  const ackBadge = document.createElement("span");
  ackBadge.className = "ack-badge";
  ackBadge.textContent = event.ack_status || "pending";

  heading.append(eventType, ackBadge);

  const details = document.createElement("dl");
  details.className = "details";
  addDetail(details, "Object", event.object_type);
  addDetail(details, "Track", `#${event.track_id}`);
  addDetail(details, "Confidence", formatConfidence(event.confidence));
  addDetail(details, "Camera", event.camera_id);
  addDetail(details, "Time", formatTimestamp(event.timestamp));

  const actions = document.createElement("div");
  actions.className = "actions";
  actions.append(
    createAckButton("Confirm", "confirmed", event.event_id),
    createAckButton("Reject", "rejected", event.event_id),
  );

  body.append(heading, details, actions);
  if (event.evidence_path) {
    const evidence = document.createElement("img");
    evidence.className = "evidence";
    evidence.src = evidenceUrl(event.evidence_path);
    evidence.alt = `Evidence snapshot for ${event.event_type}`;
    evidence.addEventListener("error", () => {
      evidence.classList.add("missing");
      evidence.alt = "Evidence snapshot unavailable";
    });
    article.append(evidence, body);
  } else {
    article.classList.add("no-evidence");
    article.append(body);
  }

  if ((event.ack_status || "pending") !== "pending") {
    markHandled(article, event.ack_status);
  }

  return article;
}

function addDetail(details, label, value) {
  const wrapper = document.createElement("div");
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value;
  wrapper.append(term, description);
  details.append(wrapper);
}

function createAckButton(label, status, eventId) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.action = status;
  button.textContent = label;
  button.addEventListener("click", () => acknowledge(eventId, status));
  return button;
}

async function acknowledge(eventId, status) {
  const element = renderedEvents.get(eventId);
  if (!element) {
    return;
  }

  setButtonsDisabled(element, true);
  try {
    const response = await fetch(`${API_BASE_URL}/events/${eventId}/ack`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const updatedEvent = await response.json();
    markHandled(element, updatedEvent.ack_status);
  } catch (error) {
    connectionStatus.textContent = `Ack failed: ${error.message}`;
    setButtonsDisabled(element, false);
  }
}

function syncAckState(element, event) {
  const status = event.ack_status || "pending";
  if (status !== "pending" && element.dataset.ackStatus !== status) {
    markHandled(element, status);
  }
}

function markHandled(element, status) {
  element.dataset.ackStatus = status;
  element.classList.add("handled");
  element.querySelector(".ack-badge").textContent = status;
  const actions = element.querySelector(".actions");
  actions.innerHTML = `<span class="handled-label">${status}</span>`;
  updateSummary();
}

function setButtonsDisabled(element, disabled) {
  element.querySelectorAll("button").forEach((button) => {
    button.disabled = disabled;
  });
}

function updateSummary() {
  const activeCount = [...renderedEvents.values()].filter(
    (element) => element.dataset.ackStatus === "pending",
  ).length;
  alertCount.textContent = String(activeCount);
  emptyState.hidden = renderedEvents.size > 0;
}

function toggleCamera() {
  const shouldOpen = cameraPanel.hidden;
  cameraPanel.hidden = !shouldOpen;
  cameraToggle.textContent = shouldOpen ? "Close Camera" : "Open Camera";
  cameraFeed.src = shouldOpen ? `${API_BASE_URL}/video_feed` : "";
}

function evidenceUrl(evidencePath) {
  const filename = String(evidencePath || "").split(/[\\/]/).pop();
  return `${API_BASE_URL}/evidence/${encodeURIComponent(filename)}`;
}

function severityClass(eventType) {
  if (ALARM_EVENT_TYPES.has(eventType)) {
    return "high";
  }
  if (eventType === "NEW_OBJECT_DETECTED") {
    return "info";
  }
  return "normal";
}

function formatConfidence(confidence) {
  return Number(confidence).toFixed(2);
}

function formatTimestamp(timestamp) {
  return new Date(timestamp).toLocaleString();
}

function triggerAlarm() {
  playAlarmBeep();
  alarmBanner.hidden = false;
  alarmBanner.classList.remove("flash");
  void alarmBanner.offsetWidth;
  alarmBanner.classList.add("flash");
  window.setTimeout(() => {
    alarmBanner.hidden = true;
  }, 1800);
}

function playAlarmBeep() {
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) {
    return;
  }

  audioContext = audioContext || new AudioContext();
  if (audioContext.state === "suspended") {
    audioContext.resume();
  }
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  oscillator.type = "square";
  oscillator.frequency.value = 880;
  gain.gain.setValueAtTime(0.0001, audioContext.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.18, audioContext.currentTime + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + 0.22);
  oscillator.connect(gain);
  gain.connect(audioContext.destination);
  oscillator.start();
  oscillator.stop(audioContext.currentTime + 0.24);
}

function unlockAudio() {
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) {
    return;
  }
  audioContext = audioContext || new AudioContext();
  if (audioContext.state === "suspended") {
    audioContext.resume();
  }
}
