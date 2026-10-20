"use strict";

// This browser polls read-only validated evidence; it never starts a scenario.
const seen = new Set();
const timeline = document.getElementById("timeline");
const keyFor = (event) => [event.timestamp, event.run, event.scenario, event.control, event.decision, event.reason].join("\u0000");
const text = (node, value) => { node.textContent = String(value ?? ""); };

const json = (value) => JSON.stringify(value, null, 2);
const fallback = (event) => ({ details: { input: { input_sha256: event.input_sha256 }, control: { name: event.control }, observation: { decision: event.decision, reason: event.reason }, state: { decision: event.decision } }, observation_kind: "hash_only", event_sha256: "visual artifact pending" });
const linked = (event, visual) => visual.find((item) => item.timestamp === event.timestamp && item.scenario === event.scenario && item.control === event.control && item.decision === event.decision) || fallback(event);

// Use textContent for every evidence field so captured data cannot become markup.
const addEvent = (event, visual) => {
  const fragment = document.getElementById("live-evidence-template").content.cloneNode(true);
  const item = fragment.querySelector("li");
  item.className = `event event-${event.run.toLowerCase()}`;
  text(fragment.querySelector("strong"), `[${event.run}] ${event.scenario} ${event.label} ${event.control} -> ${event.decision}`);
  text(fragment.querySelector("span"), event.reason);
  text(fragment.querySelector(".input"), json(visual.details.input || { input_sha256: event.input_sha256 }));
  text(fragment.querySelector(".control"), json(visual.details.control || { name: event.control }));
  text(fragment.querySelector(".observation"), json(visual.details.observation || { decision: event.decision }));
  text(fragment.querySelector(".state"), json(visual.details.state || { decision: event.decision }));
  text(fragment.querySelector(".binding"), json({ observation_kind: visual.observation_kind, event_sha256: visual.event_sha256, input_sha256: event.input_sha256, aisvs_ids: event.aisvs_ids }));
  timeline.appendChild(fragment);
  text(document.getElementById("active-title"), `${event.scenario}: ${event.control}`);
  text(document.getElementById("active-detail"), `${event.run} recorded ${event.decision}. This is evidence playback, not browser execution.`);
  text(document.getElementById("active-event"), JSON.stringify(event, null, 2));
};

const poll = async () => {
  try {
    const response = await fetch("/live/observations.json", { cache: "no-store" });
    if (!response.ok) throw new Error("evidence unavailable");
    const data = await response.json();
    const events = [...data.runs.A, ...data.runs.B].sort((left, right) => left.timestamp.localeCompare(right.timestamp));
    events.forEach((event) => {
      const key = keyFor(event);
      if (!seen.has(key)) { seen.add(key); addEvent(event, linked(event, data.visual_runs[event.run] || [])); }
    });
    text(document.getElementById("meta"), `${events.length} validated evidence event(s) observed. Polling every 700 ms.`);
  } catch (_) {
    text(document.getElementById("meta"), "Waiting for valid evidence files...");
  }
  window.setTimeout(poll, 700);
};

poll();
