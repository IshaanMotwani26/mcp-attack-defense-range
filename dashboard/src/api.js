// Thin client for the range backend. REST for catalog + history,
// a WebSocket for the live scan stream.

export async function getScenarios() {
  const r = await fetch("/api/scenarios");
  return (await r.json()).scenarios;
}

export async function getRuns() {
  const r = await fetch("/api/runs");
  return (await r.json()).runs;
}

export async function getRun(id) {
  const r = await fetch(`/api/runs/${id}`);
  return await r.json();
}

export async function resetPins() {
  await fetch("/api/pins/reset", { method: "POST" });
}

// Open a scan. `onEvent` is called with each streamed event object.
// Returns the WebSocket so the caller can close it if needed.
export function openScan(scenarioId, onEvent) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/scan/${scenarioId}`);
  ws.onmessage = (e) => onEvent(JSON.parse(e.data));
  ws.onerror = () => onEvent({ event: "error", message: "socket error" });
  return ws;
}
