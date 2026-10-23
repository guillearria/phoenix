"use strict";

const $ = (id) => document.getElementById(id);
const KEY = "daylight-saving-schedule-v1";
const EXAMPLE = [
  ["Wake up", "06:30"], ["Breakfast", "07:00"], ["Lunch", "11:30"],
  ["Nap", "12:30"], ["Dinner", "17:00"], ["Bedtime", "19:00"],
];
let lastText = "";
let rowId = 0;

// Dates are plain calendar days in local time, never instants.
function ymd(d) {
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}
function parseYmd(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || "");
  return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
}
function addDays(d, n) { const e = new Date(d); e.setDate(e.getDate() + n); return e; }
function dayName(d) { return d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" }); }
function longName(d) { return d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" }); }

// The nth Sunday of a month (n = -1 for the last one).
function sunday(y, month, n) {
  if (n > 0) {
    const first = new Date(y, month, 1);
    return new Date(y, month, 1 + ((7 - first.getDay()) % 7) + 7 * (n - 1));
  }
  const last = new Date(y, month + 1, 0);
  return new Date(y, month, last.getDate() - last.getDay());
}

// US and Canada: second Sunday of March, first Sunday of November.
// UK and Europe: last Sunday of March, last Sunday of October.
function nextChange(today, region) {
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  for (const y of [t.getFullYear(), t.getFullYear() + 1]) {
    const list = region === "us"
      ? [[sunday(y, 2, 2), "forward"], [sunday(y, 10, 1), "back"]]
      : [[sunday(y, 2, -1), "forward"], [sunday(y, 9, -1), "back"]];
    for (const [d, dir] of list) if (d >= t) return { date: d, dir };
  }
}

function fmt(min) {
  const m = ((min % 1440) + 1440) % 1440;
  const h = Math.floor(m / 60), mm = m % 60;
  return ((h + 11) % 12 + 1) + ":" + String(mm).padStart(2, "0") + (h < 12 ? " am" : " pm");
}
function toMin(s) {
  const m = /^(\d{1,2}):(\d{2})/.exec(s || "");
  return m ? +m[1] * 60 + +m[2] : null;
}
function shiftWords(n) {
  if (n === 0) return "usual times";
  return Math.abs(n) + " min " + (n > 0 ? "later" : "earlier") + " than usual";
}

function el(tag, text, cls) {
  const e = document.createElement(tag);
  if (text != null) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}

function addRow(what, time) {
  const id = ++rowId;
  const row = el("div", null, "item");
  const a = el("div"), b = el("div");
  const la = el("label", "What"), ia = el("input");
  la.htmlFor = "what-" + id; ia.id = la.htmlFor; ia.type = "text"; ia.value = what || "";
  ia.placeholder = "Bedtime"; ia.className = "what";
  const lb = el("label", "Usual time"), ib = el("input");
  lb.htmlFor = "time-" + id; ib.id = lb.htmlFor; ib.type = "time"; ib.value = time || ""; ib.className = "time";
  a.append(la, ia); b.append(lb, ib);
  const rm = el("button", "Remove", "secondary");
  rm.type = "button";
  const label = () => rm.setAttribute("aria-label", "Remove " + (ia.value.trim() || "this time"));
  label();
  ia.addEventListener("input", label);
  rm.addEventListener("click", () => {
    const next = row.nextElementSibling || row.previousElementSibling;
    row.remove();
    if (!$("items").children.length) addRow();
    (next ? next.querySelector("input") : $("add")).focus();
    changed();
  });
  row.append(a, b, rm);
  $("items").append(row);
  return ia;
}

function readItems() {
  const out = [];
  let k = 0;
  for (const row of $("items").children) {
    k++;
    const min = toMin(row.querySelector(".time").value);
    if (min == null) continue;
    out.push({ what: row.querySelector(".what").value.trim() || "Time " + k, min });
  }
  return out;
}

function radio(name) { return document.querySelector('input[name="' + name + '"]:checked').value; }
function setRadio(name, v) { document.querySelector('input[name="' + name + '"][value="' + v + '"]').checked = true; }

// The plan, as a list of days. Each day carries how far its clock times sit from the usual ones.
// Clocks go back: the body runs an hour ahead of the new clock, so times move later each day.
// Clocks go forward: the opposite. Before the change you move toward the new clock;
// after it you start near the old clock and move back to your usual times.
function makePlan(change, dir, step, when) {
  const n = 60 / step, sign = dir === "back" ? 1 : -1;
  const days = [];
  if (when === "before") {
    for (let k = n; k >= 1; k--) {
      days.push({ date: addDays(change, -k), shift: sign * step * (n - k + 1),
        tag: k === 1 ? "Clocks change tonight" : "" });
    }
    days.push({ date: change, shift: 0, change: true,
      tag: "Clocks changed overnight. Usual times on the new clock." });
  } else {
    days.push({ date: addDays(change, -1), shift: 0, tag: "Usual times. Clocks change tonight." });
    for (let i = 0; i < n; i++) {
      const shift = -sign * (60 - step * (i + 1));
      days.push({ date: addDays(change, i), shift, change: i === 0,
        tag: i === 0 ? "Clocks changed overnight" : (shift === 0 ? "Back to usual times" : "") });
    }
  }
  return days;
}

function render() {
  const items = readItems();
  const change = parseYmd($("date").value);
  const dir = radio("dir"), when = radio("when");
  const step = parseInt($("step").value, 10);
  const sum = $("summary"), out = $("days");
  out.replaceChildren();
  lastText = "";
  sum.className = "summary";
  if (!items.length || !change) {
    sum.className = "summary error";
    sum.textContent = !items.length ? "Add at least one time to your usual day." : "Pick the date the clocks change.";
    $("copy").disabled = $("print").disabled = true;
    return;
  }
  $("copy").disabled = $("print").disabled = false;

  const days = makePlan(change, dir, step, when);
  const n = 60 / step, way = dir === "back" ? "later" : "earlier";
  const goes = dir === "back" ? "go back" : "go forward";
  if (when === "before") {
    sum.textContent = "Move everything " + step + " minutes " + way + " each day for " + n + " days, starting " +
      dayName(days[0].date) + ". On " + dayName(change) + ", after the clocks " + goes +
      ", you are on your usual times.";
  } else {
    sum.textContent = "Keep your usual times until the clocks " + goes + ". On " + dayName(change) +
      ", start " + (60 - step) + " minutes " + (dir === "back" ? "before" : "after") +
      " your usual times and move " + step + " minutes " + way + " each day. By " +
      dayName(days[days.length - 1].date) + " you are on your usual times.";
  }

  const lines = [sum.textContent, ""];
  for (const d of days) {
    const box = el("div", null, "day" + (d.change ? " change" : ""));
    const h = el("h3", dayName(d.date));
    h.append(el("span", (d.tag ? d.tag + ". " : "") + (d.shift === 0 ? "" : shiftWords(d.shift) + "."), "tag"));
    const ul = el("ul");
    const parts = [];
    for (const it of items) {
      const li = el("li");
      li.append(el("span", it.what), el("b", fmt(it.min + d.shift)));
      ul.append(li);
      parts.push(it.what + " " + fmt(it.min + d.shift));
    }
    box.append(h, ul);
    out.append(box);
    lines.push(dayName(d.date) + (d.tag ? " (" + d.tag.replace(/\.$/, "") + ")" : "") + ": " + parts.join(", "));
  }
  lastText = lines.join("\n");
}

function showNext() {
  const today = new Date();
  const us = nextChange(today, "us"), eu = nextChange(today, "eu");
  const say = (c) => longName(c.date) + ", clocks go " + c.dir;
  $("next").textContent = "Next change. US and Canada: " + say(us) + ". UK and Europe: " + say(eu) + ".";
  return { us, eu };
}

function save() {
  try {
    const items = [...$("items").children].map((r) => [r.querySelector(".what").value, r.querySelector(".time").value]);
    localStorage.setItem(KEY, JSON.stringify({
      items, date: $("date").value, dir: radio("dir"), step: $("step").value, when: radio("when"),
    }));
  } catch (e) { /* storage off: fine */ }
}

function load() {
  try {
    const d = JSON.parse(localStorage.getItem(KEY) || "null");
    if (!d || !Array.isArray(d.items)) return false;
    for (const [w, t] of d.items) addRow(w, t);
    if (!d.items.length) addRow();
    $("date").value = d.date || "";
    if (d.dir) setRadio("dir", d.dir);
    if (d.when) setRadio("when", d.when);
    if (d.step) $("step").value = d.step;
    return true;
  } catch (e) { return false; }
}

function changed() {
  $("example-note").hidden = true;
  $("copied").textContent = "";
  render();
  save();
}

const next = showNext();
const use = (c) => { $("date").value = ymd(c.date); setRadio("dir", c.dir); changed(); };
$("use-us").addEventListener("click", () => use(next.us));
$("use-eu").addEventListener("click", () => use(next.eu));
$("add").addEventListener("click", () => { addRow().focus(); });
document.querySelector("main").addEventListener("input", (e) => {
  if (e.target.closest("#items, fieldset") || ["date", "step"].includes(e.target.id)) changed();
});
document.querySelector("main").addEventListener("change", (e) => {
  if (e.target.type === "radio" || ["date", "step"].includes(e.target.id)) changed();
});
$("print").addEventListener("click", () => window.print());
$("copy").addEventListener("click", async () => {
  if (!lastText) return;
  try {
    await navigator.clipboard.writeText(lastText);
    $("copied").textContent = "Copied.";
  } catch (e) {
    $("copied").textContent = "Could not copy. Select the plan and copy it by hand.";
  }
});
$("clear").addEventListener("click", () => {
  $("items").replaceChildren();
  addRow();
  $("date").value = ymd(next.us.date);
  setRadio("dir", next.us.dir);
  setRadio("when", "before");
  $("step").value = "15";
  changed();  // saves the empty day, so a reload stays empty
  $("items").querySelector("input").focus();
});

if (load()) {
  $("example-note").hidden = true;
} else {
  for (const [w, t] of EXAMPLE) addRow(w, t);
  $("date").value = ymd(next.us.date);
  setRadio("dir", next.us.dir);
  $("example-when").textContent = longName(next.us.date) + ", clocks go " + next.us.dir;
}
render();  // the example plan is visible before anyone types
