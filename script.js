// Get references to HTML elements
const scanCountEl = document.getElementById("scanCount");
const joinCountEl = document.getElementById("joinCount");
const joinBtn = document.getElementById("joinBtn");

// Determine WebSocket URL dynamically
function getWebSocketUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}

let ws;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 2000;

function connectWebSocket() {
  try {
    ws = new WebSocket(getWebSocketUrl());
    reconnectAttempts = 0;

    ws.onopen = () => {
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        scanCountEl.textContent = data.scanCount;
        joinCountEl.textContent = data.joinCount;
      } catch (e) {
        console.error("Error parsing WebSocket message:", e);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected. Attempting to reconnect...");
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        setTimeout(connectWebSocket, RECONNECT_DELAY * reconnectAttempts);
      } else {
        console.error("Max reconnection attempts reached");
      }
    };
  } catch (e) {
    console.error("Error connecting WebSocket:", e);
  }
}

// Join button with proper error handling
joinBtn.addEventListener("click", async () => {
  joinBtn.disabled = true;
  const originalText = joinBtn.textContent;

  try {
    const response = await fetch("/api/join", { method: "POST" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    joinBtn.textContent = "Thank You! 🌿";
  } catch (error) {
    console.error("Error joining:", error);
    joinBtn.textContent = "Error - Try Again";
    joinBtn.disabled = false;
  }
});

// Register scan on page load with error handling
async function registerScan() {
  try {
    const response = await fetch("/api/scan", { method: "POST" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
  } catch (error) {
    console.error("Error registering scan:", error);
  }
}

// Initialize
connectWebSocket();
registerScan();