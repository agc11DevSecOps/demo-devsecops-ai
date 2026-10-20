"use strict";

// Load only bundle assets verified by the loopback server before it exposes them.
const loadJson = async (name) => {
  const response = await fetch(name, { cache: "no-store" });
  if (!response.ok) return null;
  return response.json();
};

const text = (node, value) => { node.textContent = String(value ?? ""); };

const json = (value) => JSON.stringify(value, null, 2);
const fallback = (event) => ({
  observation_kind: event.label === "SCRIPTED" || event.label === "DESIGNED" ? "fixture" : "observed",
  details: { input: { input_sha256: event.input_sha256 }, control: { name: event.control }, observation: { decision: event.decision, reason: event.reason }, state: { decision: event.decision } },
  event_sha256: "visual artifact unavailable for this historical event",
});

const linked = (event, visual) => visual.find((item) => item.timestamp === event.timestamp && item.scenario === event.scenario && item.control === event.control && item.decision === event.decision) || fallback(event);

// Bind each display record to its hash-only AISVS event before rendering text.
const renderDossier = (runs, visualRuns) => {
  const target = document.getElementById("dossier");
  const template = document.getElementById("evidence-template");
  const ordered = [...runs.A, ...runs.B].sort((left, right) => left.timestamp.localeCompare(right.timestamp));
  return ordered.map((event, index) => {
    const visual = linked(event, visualRuns[event.run] || []);
    const details = visual.details;
    const fragment = template.content.cloneNode(true);
    const step = fragment.querySelector(".evidence-step");
    step.dataset.index = String(index);
    step.classList.add(`evidence-${event.run.toLowerCase()}`);
    text(fragment.querySelector(".eyebrow"), `${event.run} · ${event.scenario} · ${visual.observation_kind.toUpperCase()} · ${event.label}`);
    text(fragment.querySelector("h3"), `${event.control} → ${event.decision}`);
    text(fragment.querySelector(".reason"), event.reason);
    text(fragment.querySelector(".input"), json(details.input || { input_sha256: event.input_sha256 }));
    text(fragment.querySelector(".control"), json(details.control || { name: event.control }));
    text(fragment.querySelector(".observation"), json(details.observation || { decision: event.decision }));
    text(fragment.querySelector(".state"), json(details.state || { decision: event.decision }));
    text(fragment.querySelector(".binding"), json({ event_sha256: visual.event_sha256, input_sha256: event.input_sha256, aisvs_ids: event.aisvs_ids }));
    target.appendChild(fragment);
    return step;
  });
};

// Replay changes only browser focus; it never re-executes a scenario or control.
const enablePlayback = (steps) => {
  let index = -1;
  let timer = null;
  const position = document.getElementById("replay-position");
  const show = () => {
    if (!steps.length) return;
    index = (index + 1) % steps.length;
    steps.forEach((step, item) => step.classList.toggle("active", item === index));
    steps[index].scrollIntoView({ behavior: "smooth", block: "center" });
    text(position, `${index + 1} / ${steps.length} controls`);
  };
  document.getElementById("replay-next").addEventListener("click", show);
  document.getElementById("replay-play").addEventListener("click", (event) => {
    if (timer) { window.clearInterval(timer); timer = null; text(event.currentTarget, "Autoplay"); return; }
    show(); timer = window.setInterval(show, 1800); text(event.currentTarget, "Pause replay");
  });
  text(position, `${steps.length} controls ready`);
};

const renderChallenge = (challenge, response, replay) => {
  if (!challenge || !response) return;
  const state = response.nonce_match ? "MATCH" : "MISMATCH";
  text(document.getElementById("challenge-status"), `Local model result: ${state}. Replay: ${replay?.status ?? "NOT RUN"}.`);
  text(document.getElementById("challenge-detail"), [
    `Nonce: ${challenge.nonce}`,
    `Answer: ${response.answer}`,
    `Model: ${response.model}`,
    `Answer SHA-256: ${response.answer_sha256}`,
  ].join("\n"));
};

Promise.all([loadJson("manifest.json"), loadJson("observations.json"), loadJson("dossier.json"), loadJson("challenge.json"), loadJson("response.json"), loadJson("replay.json")])
  .then(([manifest, observations, dossier, challenge, response, replay]) => {
    if (!manifest || !observations) throw new Error("bundle unavailable");
    text(document.getElementById("meta"), `Bundle format ${manifest.format_version}. Assets are SHA-256 pinned; browser rendering is display-only.`);
    enablePlayback(renderDossier(observations.runs, dossier?.runs || { A: [], B: [] }));
    renderChallenge(challenge, response, replay);
  })
  .catch(() => text(document.getElementById("meta"), "Validated bundle data is unavailable."));
