"use strict";

const $ = (id) => document.getElementById(id);
const KEY = "golf-groups-v1";
let last = null;

// Groups of exactly the size you chose, with only the last group smaller.
// 18 players in fives gives 5, 5, 5, 3. A leftover of one player is never a group of one:
// 16 in fives gives 5, 5, 3, 3.
function groupSizes(n, size) {
  const full = Math.floor(n / size), rest = n % size;
  const sizes = Array(full).fill(size);
  if (rest === 1 && full > 0 && size === 2) {
    sizes[sizes.length - 1] = 3;
  } else if (rest === 1 && full > 0) {
    sizes.pop();
    sizes.push(Math.ceil((size + 1) / 2), Math.floor((size + 1) / 2));
  } else if (rest > 0) {
    sizes.push(rest);
  }
  return sizes;
}

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// Cost of putting a pair together again: grows fast with each repeat.
const w = (m) => m * m;

// One round: random start, then swap players between groups while it helps.
function makeRound(c, n, sizes) {
  const order = shuffle([...Array(n).keys()]);
  const groups = [];
  let k = 0;
  for (const s of sizes) { groups.push(order.slice(k, k + s)); k += s; }
  let better = true;
  while (better) {
    better = false;
    for (let A = 0; A < groups.length; A++) {
      for (let B = A + 1; B < groups.length; B++) {
        const ga = groups[A], gb = groups[B];
        for (let i = 0; i < ga.length; i++) {
          for (let j = 0; j < gb.length; j++) {
            const a = ga[i], b = gb[j];
            let d = 0;
            for (const x of ga) if (x !== a) d += w(c[b][x]) - w(c[a][x]);
            for (const y of gb) if (y !== b) d += w(c[a][y]) - w(c[b][y]);
            if (d < 0) { ga[i] = b; gb[j] = a; better = true; }
          }
        }
      }
    }
  }
  return groups;
}

function emptyCounts(n) {
  return Array.from({ length: n }, () => new Array(n).fill(0));
}

function addRound(c, groups) {
  for (const g of groups)
    for (let i = 0; i < g.length; i++)
      for (let j = i + 1; j < g.length; j++) { c[g[i]][g[j]]++; c[g[j]][g[i]]++; }
}

function score(c, n) {
  let s = 0;
  for (let i = 0; i < n; i++)
    for (let j = i + 1; j < n; j++) if (c[i][j] > 1) s += (c[i][j] - 1) ** 2;
  return s;
}

// Build many whole schedules for about half a second and keep the best one.
function makeSchedule(n, size, rounds) {
  const sizes = groupSizes(n, size);
  const stop = Date.now() + 500;
  let best = null;
  do {
    const c = emptyCounts(n);
    const plan = [];
    for (let r = 0; r < rounds; r++) {
      let pick = null, pickCost = Infinity;
      for (let t = 0; t < 4; t++) {
        const g = makeRound(c, n, sizes);
        let cost = 0;
        for (const grp of g)
          for (let i = 0; i < grp.length; i++)
            for (let j = i + 1; j < grp.length; j++) cost += w(c[grp[i]][grp[j]]);
        if (cost < pickCost) { pick = g; pickCost = cost; }
      }
      addRound(c, pick);
      plan.push(pick);
    }
    const s = score(c, n);
    if (!best || s < best.s) best = { plan, c, s };
  } while (best.s > 0 && Date.now() < stop);
  return best;
}

function readNames() {
  const seen = new Set();
  const names = [];
  for (const raw of $("names").value.split("\n")) {
    const name = raw.trim();
    if (!name) continue;
    let unique = name, k = 2;
    while (seen.has(unique)) unique = name + " (" + k++ + ")";
    seen.add(unique);
    names.push(unique);
  }
  return names;
}

function num(id, lo, hi) {
  const v = parseInt($(id).value, 10);
  if (isNaN(v)) return lo;
  return Math.min(hi, Math.max(lo, v));
}

function updateMath() {
  const n = readNames().length;
  const size = num("size", 2, 12), rounds = num("rounds", 1, 60);
  const el = $("math");
  el.className = "hint";
  if (n < 2) { el.textContent = "Add at least two names."; return; }
  if (size >= n) { el.textContent = "Everyone fits in one group. Lower the group size."; return; }
  const sizes = groupSizes(n, size);
  const shape = sizes.every((s) => s === sizes[0])
    ? sizes.length + " groups of " + sizes[0]
    : sizes.length + " groups (" + sizes.join(", ") + ")";
  const meets = (size - 1) * rounds;
  let msg = n + " players make " + shape + " each round. ";
  if (meets > n - 1) {
    msg += "Each person fills up to " + meets + " partner spots, but there are only " + (n - 1) +
      " others, so some repeats can't be avoided.";
  } else {
    msg += "Each person can meet up to " + meets + " of the " + (n - 1) + " others.";
  }
  el.textContent = msg;
}

function el(tag, text, cls) {
  const e = document.createElement(tag);
  if (text != null) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}

function render(names, result) {
  const n = names.length;
  const { plan, c } = result;
  let twice = 0, never = 0, most = 0;
  for (let i = 0; i < n; i++)
    for (let j = i + 1; j < n; j++) {
      if (c[i][j] > 1) twice++;
      if (c[i][j] === 0) never++;
      most = Math.max(most, c[i][j]);
    }
  let sum = twice === 0
    ? "Nobody shares a group with the same person twice."
    : twice + " pairs share a group more than once. The most any pair meets is " + most + " times.";
  if (never > 0) sum += " " + never + " pairs never meet.";
  else sum += " Everyone meets everyone.";
  $("summary").textContent = sum;

  const out = $("rounds-out");
  out.replaceChildren();
  const seen = emptyCounts(n);
  plan.forEach((groups, r) => {
    const box = el("div", null, "round");
    box.append(el("h3", "Round " + (r + 1)));
    const ul = el("ul", null, "groups");
    groups.forEach((g, gi) => {
      const li = el("li");
      li.append(el("b", "Group " + (gi + 1)));
      li.append(document.createTextNode(g.map((p) => names[p]).join(", ")));
      const again = [];
      for (let i = 0; i < g.length; i++)
        for (let j = i + 1; j < g.length; j++)
          if (seen[g[i]][g[j]] > 0) again.push(names[g[i]] + " & " + names[g[j]]);
      if (again.length) {
        li.append(el("br"));
        li.append(el("span", "Again: " + again.join("; "), "repeat"));
      }
      ul.append(li);
    });
    addRound(seen, groups);
    box.append(ul);
    out.append(box);
  });

  const pp = $("per-player");
  pp.replaceChildren();
  names.forEach((name, i) => {
    const met = [], missed = [];
    names.forEach((other, j) => {
      if (i === j) return;
      if (c[i][j] > 0) met.push(other + (c[i][j] > 1 ? " ×" + c[i][j] : ""));
      else missed.push(other);
    });
    let t = name + ": " + (met.join(", ") || "nobody");
    if (missed.length) t += ". Never: " + missed.join(", ");
    pp.append(el("p", t, "pp"));
  });

  $("out").hidden = false;
}

function asText(names, plan) {
  return plan.map((groups, r) =>
    "Round " + (r + 1) + "\n" +
    groups.map((g, gi) => "  Group " + (gi + 1) + ": " + g.map((p) => names[p]).join(", ")).join("\n")
  ).join("\n\n");
}

function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify({
      names: $("names").value, count: $("count").value,
      size: $("size").value, rounds: $("rounds").value,
    }));
  } catch (e) { /* storage off: fine */ }
}

function load() {
  try {
    const d = JSON.parse(localStorage.getItem(KEY) || "null");
    if (!d) return;
    for (const k of ["names", "count", "size", "rounds"]) if (d[k] != null) $(k).value = d[k];
  } catch (e) { /* ignore */ }
}

function run(quiet) {
  const names = readNames();
  const size = num("size", 2, 12), rounds = num("rounds", 1, 60);
  if (names.length < 2 || size >= names.length) {
    updateMath();
    $("math").className = "hint error";
    $("math").focus();
    return;
  }
  save();
  $("copied").textContent = "";
  last = { names, result: makeSchedule(names.length, size, rounds) };
  render(names, last.result);
  if (!quiet) $("result").scrollIntoView({ behavior: "smooth" });
}

$("fill").addEventListener("click", () => {
  const n = num("count", 2, 200);
  $("names").value = Array.from({ length: n }, (_, i) => "Player " + (i + 1)).join("\n");
  updateMath();
  save();
});
$("make").addEventListener("click", () => run(false));
$("again").addEventListener("click", () => run(false));
$("print").addEventListener("click", () => window.print());
$("copy").addEventListener("click", async () => {
  if (!last) return;
  const text = asText(last.names, last.result.plan);
  try {
    await navigator.clipboard.writeText(text);
    $("copied").textContent = "Copied.";
  } catch (e) {
    $("copied").textContent = "Could not copy. Select the groups and copy them by hand.";
  }
});
$("clear").addEventListener("click", () => {
  try { localStorage.removeItem(KEY); } catch (e) { /* ignore */ }
  $("names").value = "";
  $("out").hidden = true;
  updateMath();
});
for (const id of ["names", "size", "rounds"]) $(id).addEventListener("input", () => { updateMath(); save(); });
$("math").tabIndex = -1;

load();
const firstVisit = !$("names").value.trim();
if (firstVisit) $("fill").click();
updateMath();
if (firstVisit) {
  run(true);  // the example result is visible before anyone types
} else {
  $("example-note").hidden = true;
}
for (const id of ["names", "size", "rounds", "count"]) {
  $(id).addEventListener("input", () => { $("example-note").hidden = true; }, { once: true });
}
