"use strict";

// Recorded A/B presentation. The browser renders only the server-validated
// projection with textContent: it never builds HTML from evidence, executes a
// scenario, calls a model or opens a tool.

const STEPS = ["Payload", "Before", "Control", "After", "Result"];
const state = { projection: null, index: 0, step: 0, view: "present" };

const $ = (id) => document.getElementById(id);
const el = (tag, className, value) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = String(value ?? "");
  return node;
};
const add = (parent, ...children) => { children.forEach((child) => { if (child) parent.appendChild(child); }); return parent; };

const valueText = (value) => {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
};

const decisionClass = (decision) => `decision decision-${String(decision || "unknown").toLowerCase().replace(/[^a-z]+/g, "-")}`;

const decisionLine = (event) => {
  const line = el("div", "decision-line");
  if (!event) { add(line, el("span", "muted", "No recorded event.")); return line; }
  add(line, el("strong", decisionClass(event.decision), event.decision || "UNKNOWN"), el("span", "label-chip", event.label || ""));
  return line;
};

const kv = (pairs) => {
  const list = el("dl", "kv");
  pairs.forEach(([key, value]) => {
    if (value === "" || value === null || value === undefined) return;
    add(list, el("dt", "", key), el("dd", typeof value === "object" ? "mono" : "", valueText(value)));
  });
  return list;
};

const excerpt = (anchor) => {
  const box = el("div", "");
  add(box, el("p", "excerpt-label", `${anchor.location}`));
  add(box, el("pre", "block mono", (anchor.lines || []).join("\n")));
  if (anchor.truncated) add(box, el("p", "muted", "Excerpt truncated for display."));
  return box;
};

const diagram = (name, caption) => {
  if (!name) return null;
  const figure = el("figure", "diagram-figure");
  const img = el("img", "");
  img.loading = "lazy";
  img.alt = caption;
  img.src = `diagram-${name}.svg`;
  add(figure, img, el("figcaption", "", caption));
  return figure;
};

const flowRows = (pairs, side) => {
  const container = el("div", "flow");
  const head = el("div", "flow-row head");
  add(head, el("span", "", "Stage"), el("span", "", side === "before" ? "Run A · no controls" : "Run B · enforced"), el("span", "", "Detail"));
  add(container, head);
  pairs.forEach((pair) => {
    (pair.flow || []).forEach((row) => {
      const cell = row[side];
      if (!cell) return;
      const line = el("div", "flow-row");
      add(line,
        el("span", "flow-stage", row.label),
        el("span", `status status-${String(cell.status).replace(/[^a-z]+/g, "-")}`, cell.status),
        el("span", "flow-detail", cell.detail || ""));
      add(container, line);
    });
  });
  return container.children.length > 1 ? container : null;
};

const eventPanel = (event, kind) => {
  const panel = el("section", `panel panel-${kind}`);
  add(panel, el("p", "eyebrow", kind === "before" ? "RUN A · WITHOUT CONTROLS" : "RUN B · CONTROLS ENFORCED"));
  add(panel, decisionLine(event));
  if (event) add(panel, el("p", "reason", event.reason || ""));
  return panel;
};

const pipelineTable = (rows) => {
  const table = el("table", "table");
  const head = el("tr");
  ["Stage", "Decision", "Label", "Reason"].forEach((name) => add(head, el("th", "", name)));
  const thead = el("thead");
  add(thead, head);
  add(table, thead);
  const body = el("tbody");
  rows.forEach((row) => {
    const tr = el("tr");
    add(tr, el("td", "", row.control), el("td", "", row.decision), el("td", "", row.label), el("td", "", row.reason));
    add(body, tr);
  });
  add(table, body);
  return table;
};

const renderPayload = (card) => {
  const wrap = el("div", "");
  add(wrap, el("p", "eyebrow", "SAFE SYNTHETIC PAYLOAD"), el("h3", "", card.payload_kind));
  const list = el("dl", "kv");
  (card.payload || []).forEach((item) => {
    add(list, el("dt", "mono", item.key), el("dd", "mono", valueText(item.value)));
  });
  add(wrap, list);
  add(wrap, el("p", "muted", `Reality: ${card.reality}`));
  if (card.appendix) add(wrap, el("p", "notice", "Appendix: only a complete admitted campaign counts. A reduced run stays PARTIAL."));
  if (card.pairs.length > 1) {
    add(wrap, el("p", "muted", `This scenario records ${card.pairs.length} sub-cases: ${card.pairs.map((pair) => pair.label).join(", ")}.`));
  }
  return wrap;
};

const renderBefore = (card) => {
  const wrap = el("div", "");
  const grid = el("div", `pairs${card.pairs.length > 1 ? " two-up" : ""}`);
  card.pairs.forEach((pair) => {
    const block = el("div", "");
    add(block, el("p", "eyebrow", `CASE · ${pair.label}`));
    add(block, eventPanel(pair.before, "before"));
    const rows = flowRows([pair], "before");
    if (rows) add(block, rows);
    add(grid, block);
  });
  add(wrap, grid);
  add(wrap, diagram(card.diagrams.before, `Run A flow: ${card.title}`));
  return wrap;
};

const renderControl = (card) => {
  const wrap = el("div", "");
  add(wrap, el("p", "muted", "Each control below is implemented in this repository. The excerpt is extracted from the source when the projection is built."));
  const list = el("div", "control-list");
  (card.controls || []).forEach((control) => {
    const box = el("article", "control");
    const head = el("div", "control-head");
    add(head, el("h3", "", control.name), el("span", "flag", control.flag || "always on"));
    add(box, head);
    add(box, el("div", "control-meta", `stage: ${control.stage}`), el("div", "control-meta", `version: ${control.version}`));
    add(box, el("p", "", control.what));
    if (control.implementation) {
      add(box, el("p", "excerpt-label", "Implementation"), excerpt(control.implementation));
    }
    if (control.integration) {
      add(box, el("p", "excerpt-label", "Integration in the flow"), excerpt(control.integration));
    }
    add(box, el("div", "absent", `Without it (Run A): ${control.absent}`));
    if (control.results && control.results.length) {
      const results = el("ul", "results");
      control.results.forEach((result) => {
        add(results, el("li", "", `${result.control} → ${result.decision} (${result.label}): ${result.reason}`));
      });
      add(box, el("p", "excerpt-label", "Recorded Run B results"), results);
    }
    add(list, box);
  });
  add(wrap, list);
  return wrap;
};

const renderAfter = (card) => {
  const wrap = el("div", "");
  if (card.scenario === "PIPELINE") {
    add(wrap, el("p", "eyebrow", "DELIVERY STAGES"), pipelineTable(card.pipeline || []));
  }
  const grid = el("div", `pairs${card.pairs.length > 1 ? " two-up" : ""}`);
  card.pairs.forEach((pair) => {
    const block = el("div", "");
    add(block, el("p", "eyebrow", `CASE · ${pair.label}`));
    add(block, eventPanel(pair.after, "after"));
    const rows = flowRows([pair], "after");
    if (rows) add(block, rows);
    add(grid, block);
  });
  if (card.pairs.length) add(wrap, grid);
  add(wrap, diagram(card.diagrams.after, `Run B flow: ${card.title}`));
  return wrap;
};

const checkPanel = (check) => {
  const box = el("article", "check");
  const head = el("div", "check-head");
  add(head, el("strong", "", check.id), el("span", `label-chip ${check.unguarded.status}`, `A: ${check.unguarded.status}`), el("span", `label-chip ${check.guarded.status}`, `B: ${check.guarded.status}`));
  add(box, head);
  if (check.unguarded.explanation) add(box, el("p", "", `Run A: ${check.unguarded.explanation}`));
  if (check.guarded.explanation) add(box, el("p", "", `Run B: ${check.guarded.explanation}`));
  return box;
};

const renderResult = (card) => {
  const wrap = el("div", "");
  const table = el("table", "table");
  const head = el("tr");
  ["Case", "Run A", "Run B", "Delta"].forEach((name) => add(head, el("th", "", name)));
  const thead = el("thead"); add(thead, head); add(table, thead);
  const body = el("tbody");
  card.pairs.forEach((pair) => {
    const tr = el("tr");
    const before = pair.before ? `${pair.before.decision} · ${pair.before.label}` : "—";
    const after = pair.after ? `${pair.after.decision} · ${pair.after.label}` : "—";
    const delta = pair.before && pair.after ? `${pair.before.decision} → ${pair.after.decision}` : "—";
    add(tr, el("td", "", pair.label), el("td", "", before), el("td", "", after), el("td", "mono", delta));
    add(body, tr);
  });
  add(table, body);
  add(wrap, table);
  if (card.pipeline && card.pipeline.length) {
    add(wrap, el("p", "muted", "Delivery pipeline stages are listed in the After step."));
  }
  const checks = card.checks || [];
  add(wrap, el("p", "eyebrow", "INSPECT · LIVE BEHAVIOURAL CHECK"));
  if (!checks.length) {
    add(wrap, el("p", "muted", "No live Inspect sample for this scenario. It is not presented as tested."));
  } else {
    const list = el("div", "checks");
    checks.forEach((check) => add(list, checkPanel(check)));
    add(wrap, list);
    const inspect = state.projection.inspect || {};
    if (inspect.view) {
      const link = el("a", "", "Open the recorded Inspect transcripts");
      link.href = inspect.view;
      link.target = "_blank";
      link.rel = "noopener";
      const line = el("p", "");
      add(line, link);
      add(wrap, line);
    }
  }
  const evidence = el("ul", "evidence");
  (card.evidence || []).forEach((path) => add(evidence, el("li", "mono", path)));
  add(wrap, el("p", "eyebrow", "EVIDENCE FILES"), evidence);
  return wrap;
};

const RENDERERS = [renderPayload, renderBefore, renderControl, renderAfter, renderResult];

const renderScenario = () => {
  const card = state.projection.scenarios[state.index];
  const root = $("scenario");
  root.replaceChildren();
  if (!card) { add(root, el("p", "muted", "No scenario evidence.")); return; }
  const head = el("div", "scenario-head");
  const left = el("div", "");
  add(left, el("p", "eyebrow", `SCENARIO ${card.scenario} · STEP ${state.step + 1} OF ${STEPS.length}`));
  const title = el("h2", "", `${card.order}. ${card.title}`);
  if (card.appendix) add(title, el("span", "badge", "Appendix"));
  add(left, title, el("p", "question", card.question));
  add(head, left, el("span", `state state-${card.state}`, card.state));
  add(root, head);
  add(root, RENDERERS[state.step](card));

  $("scenario-position").textContent = `${state.index + 1} / ${state.projection.scenarios.length}`;
  const dots = $("steps");
  dots.replaceChildren();
  STEPS.forEach((name, index) => {
    const button = el("button", `step-dot${index === state.step ? " is-active" : ""}`, name);
    button.type = "button";
    button.addEventListener("click", () => { state.step = index; renderScenario(); });
    add(dots, button);
  });
  $("prev-step").disabled = state.step === 0;
  $("next-step").disabled = state.step === STEPS.length - 1;
  $("prev-scenario").disabled = state.index === 0;
  $("next-scenario").disabled = state.index === state.projection.scenarios.length - 1;
};

const renderOverview = () => {
  const grid = $("overview-grid");
  grid.replaceChildren();
  state.projection.scenarios.forEach((card, index) => {
    const button = el("button", "overview-card");
    button.type = "button";
    add(button, el("p", "eyebrow", `SCENARIO ${card.scenario}`));
    const title = el("h3", "", `${card.order}. ${card.title}`);
    if (card.appendix) add(title, el("span", "badge", "Appendix"));
    add(button, title);
    add(button, el("p", "muted", card.question));
    const primary = card.pairs[0];
    const before = primary && primary.before ? `${primary.before.decision} · ${primary.before.label}` : "—";
    const after = primary && primary.after ? `${primary.after.decision} · ${primary.after.label}` : "—";
    add(button, el("p", "mono", `A: ${before}`), el("p", "mono", `B: ${after}`));
    add(button, el("p", `state state-${card.state}`, card.state));
    button.addEventListener("click", () => { state.index = index; state.step = 0; showView("present"); });
    add(grid, button);
  });
};

const renderMap = () => {
  const image = $("map-diagram");
  image.src = "diagram-control-integration-map.svg";
  image.onerror = () => { image.style.display = "none"; };
  const list = $("map-controls");
  list.replaceChildren();
  (state.projection.controls || []).forEach((control) => {
    const box = el("article", "control");
    add(box, el("h3", "", control.name), el("p", "flag", control.flag || "always on"));
    add(box, el("div", "control-meta", `stage: ${control.stage}`), el("div", "control-meta", control.version));
    add(box, el("p", "", control.what));
    if (control.implementation) add(box, el("p", "mono muted", control.implementation.location));
    if (control.integration) add(box, el("p", "mono muted", control.integration.location));
    add(list, box);
  });
};

const showView = (view) => {
  state.view = view;
  ["overview", "present", "map"].forEach((name) => { $(name).hidden = name !== view; });
  ["overview", "present", "map"].forEach((name) => {
    $(`tab-${name}`).classList.toggle("is-active", name === view);
  });
  if (view === "overview") renderOverview();
  if (view === "present") renderScenario();
  if (view === "map") renderMap();
};

const renderHeader = () => {
  const projection = state.projection;
  const recording = projection.recording || {};
  const parts = [];
  if (recording.recorded_at) {
    const date = new Date(recording.recorded_at);
    parts.push(`Recorded on ${Number.isNaN(date.getTime()) ? recording.recorded_at : date.toISOString().replace("T", " ").replace(/\..*/, " UTC")}`);
  } else {
    parts.push("Live run in progress");
  }
  if (recording.total_seconds) parts.push(`${Math.floor(recording.total_seconds / 60)}m ${Math.round(recording.total_seconds % 60)}s`);
  if (recording.limit_seconds) parts.push(`recording limit ${Math.round(recording.limit_seconds / 60)}m`);
  $("recording").textContent = parts.join(" · ");
  const progress = projection.progress || { complete: 0, total: 0 };
  $("progress-text").textContent = `${progress.complete} / ${progress.total} complete`;
  $("progress-bar").style.width = progress.total ? `${Math.round((progress.complete / progress.total) * 100)}%` : "0";
  const inspect = projection.inspect || {};
  const summary = inspect.summary || {};
  if (inspect.status === "available" && summary.total) {
    $("inspect-summary").textContent = `Inspect live check: ${summary.total} samples · Run A safe ${summary.unguarded_safe ?? "?"} · Run B safe ${summary.guarded_safe ?? "?"}`;
  } else {
    $("inspect-summary").textContent = "Inspect live check: not run.";
  }
  if (recording.phases && recording.phases.length) {
    $("footnote").textContent = `Recorded evidence · phases: ${recording.phases.map((phase) => `${phase.name} ${phase.seconds}s`).join(", ")} · nothing on this page executes a scenario, a model or a tool.`;
  }
};

const bind = () => {
  $("tab-overview").addEventListener("click", () => showView("overview"));
  $("tab-present").addEventListener("click", () => showView("present"));
  $("tab-map").addEventListener("click", () => showView("map"));
  $("prev-step").addEventListener("click", () => { if (state.step > 0) { state.step -= 1; renderScenario(); } });
  $("next-step").addEventListener("click", () => { if (state.step < STEPS.length - 1) { state.step += 1; renderScenario(); } });
  $("prev-scenario").addEventListener("click", () => { if (state.index > 0) { state.index -= 1; state.step = 0; renderScenario(); } });
  $("next-scenario").addEventListener("click", () => { if (state.index < state.projection.scenarios.length - 1) { state.index += 1; state.step = 0; renderScenario(); } });
  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key === "ArrowRight") { if (state.step < STEPS.length - 1) { state.step += 1; renderScenario(); } event.preventDefault(); }
    if (event.key === "ArrowLeft") { if (state.step > 0) { state.step -= 1; renderScenario(); } event.preventDefault(); }
    if (event.key === "ArrowDown") { if (state.index < state.projection.scenarios.length - 1) { state.index += 1; state.step = 0; renderScenario(); } event.preventDefault(); }
    if (event.key === "ArrowUp") { if (state.index > 0) { state.index -= 1; state.step = 0; renderScenario(); } event.preventDefault(); }
    if (event.key === "o" || event.key === "O") showView("overview");
    if (event.key === "m" || event.key === "M") showView("map");
    if (event.key === "Escape") showView("present");
  });
};

const start = async () => {
  try {
    const response = await fetch("presentation.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.projection = await response.json();
  } catch (error) {
    $("recording").textContent = "The presentation projection is unavailable. Nothing is displayed rather than showing unverified data.";
    return;
  }
  if (!state.projection.scenarios || !state.projection.scenarios.length) {
    $("recording").textContent = "No recorded scenario evidence is available.";
    return;
  }
  renderHeader();
  bind();
  showView("present");
};

start();
