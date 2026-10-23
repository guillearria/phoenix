// Volunteer schedule maker. Runs only in this browser; saves to localStorage.
(function () {
  "use strict";

  var KEY = "volunteer-schedule-v1";
  var MAX_DATES = 100;
  var DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  var el = function (id) { return document.getElementById(id); };
  var peopleBox = el("people"), startBox = el("start"), endBox = el("end");
  var slotsBox = el("slots"), avoidBox = el("avoid"), daysBox = el("days");
  var awayBox = el("away"), resultBox = el("result"), statusBox = el("status");
  var outButtons = el("out-buttons");

  // away["Ana"]["2026-11-01"] = true
  var away = {};
  var seed = 1;
  var lastRota = null;
  var isExample = false;

  // ---- dates ----
  function iso(d) { return d.toISOString().slice(0, 10); }
  function parseIso(s) {
    var p = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || "");
    return p ? new Date(Date.UTC(+p[1], +p[2] - 1, +p[3])) : null;
  }
  function label(s) {
    return parseIso(s).toLocaleDateString(undefined, {
      weekday: "short", day: "numeric", month: "short", year: "numeric", timeZone: "UTC"
    });
  }
  function chosenDays() {
    var out = [];
    daysBox.querySelectorAll("input").forEach(function (c) { if (c.checked) out.push(+c.value); });
    return out;
  }
  function dates() {
    var a = parseIso(startBox.value), b = parseIso(endBox.value), days = chosenDays();
    var out = [];
    if (!a || !b || a > b || !days.length) return out;
    for (var d = a; d <= b && out.length < MAX_DATES; d = new Date(d.getTime() + 864e5)) {
      if (days.indexOf(d.getUTCDay()) !== -1) out.push(iso(d));
    }
    return out;
  }
  function people() {
    var seen = {}, out = [];
    peopleBox.value.split("\n").forEach(function (line) {
      var n = line.trim();
      if (n && !seen[n.toLowerCase()]) { seen[n.toLowerCase()] = true; out.push(n); }
    });
    return out;
  }

  // ---- saving ----
  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify({
        people: peopleBox.value, start: startBox.value, end: endBox.value,
        days: chosenDays(), slots: slotsBox.value, avoid: avoidBox.checked,
        away: away, seed: seed
      }));
    } catch (e) { /* private mode: work without saving */ }
  }
  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch (e) { return null; }
  }

  // ---- away grid ----
  function drawAway() {
    var ps = people(), ds = dates();
    awayBox.textContent = "";
    if (!ps.length || !ds.length) {
      var p = document.createElement("p");
      p.className = "hint";
      p.textContent = "Add names and days first.";
      awayBox.appendChild(p);
      return;
    }
    var t = document.createElement("table");
    var head = t.createTHead().insertRow();
    var corner = document.createElement("th");
    corner.textContent = "Name";
    corner.scope = "col";
    head.appendChild(corner);
    ds.forEach(function (d) {
      var th = document.createElement("th");
      th.scope = "col";
      th.textContent = label(d);
      head.appendChild(th);
    });
    var body = t.createTBody();
    ps.forEach(function (name) {
      var r = body.insertRow();
      var th = document.createElement("th");
      th.scope = "row";
      th.textContent = name;
      r.appendChild(th);
      ds.forEach(function (d) {
        var c = document.createElement("input");
        c.type = "checkbox";
        c.checked = !!(away[name] && away[name][d]);
        c.setAttribute("aria-label", name + " away on " + label(d));
        c.addEventListener("change", function () {
          away[name] = away[name] || {};
          if (c.checked) away[name][d] = true; else delete away[name][d];
          save();
        });
        r.insertCell().appendChild(c);
      });
    });
    awayBox.appendChild(t);
    if (ds.length >= MAX_DATES) {
      var w = document.createElement("p");
      w.className = "warn";
      w.textContent = "Only the first " + MAX_DATES + " days are shown.";
      awayBox.appendChild(w);
    }
  }

  // ---- making the rota ----
  function rng(s) { // small seeded random numbers, so "Try another mix" is repeatable
    return function () {
      s = (s + 0x6D2B79F5) | 0;
      var t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function make() {
    var ps = people(), ds = dates();
    var slots = Math.max(1, Math.min(20, parseInt(slotsBox.value, 10) || 1));
    var avoid = avoidBox.checked, rand = rng(seed);
    var count = {}, last = {};
    ps.forEach(function (n) { count[n] = 0; last[n] = -1; });

    var rows = ds.map(function (d, i) {
      var free = ps.filter(function (n) { return !(away[n] && away[n][d]); });
      var tie = {};
      free.forEach(function (n) { tie[n] = rand(); });
      free.sort(function (a, b) {
        if (count[a] !== count[b]) return count[a] - count[b];
        if (avoid) {
          var ra = last[a] === i - 1 ? 1 : 0, rb = last[b] === i - 1 ? 1 : 0;
          if (ra !== rb) return ra - rb;
        }
        if (last[a] !== last[b]) return last[a] - last[b];
        return tie[a] - tie[b];
      });
      var picked = free.slice(0, slots);
      picked.forEach(function (n) { count[n]++; last[n] = i; });
      return { date: d, people: picked, short: slots - picked.length };
    });
    return { rows: rows, count: count, people: ps, slots: slots };
  }

  function show(rota) {
    resultBox.textContent = "";
    statusBox.textContent = "";
    if (!rota.people.length || !rota.rows.length) {
      resultBox.textContent = "Add at least one name and one day.";
      outButtons.hidden = true;
      lastRota = null;
      return;
    }
    var t = document.createElement("table");
    var cap = t.createCaption();
    cap.textContent = "Schedule";
    var h = t.createTHead().insertRow();
    ["Day", "Who"].forEach(function (x) {
      var th = document.createElement("th"); th.scope = "col"; th.textContent = x; h.appendChild(th);
    });
    var b = t.createTBody(), short = 0;
    rota.rows.forEach(function (r) {
      var tr = b.insertRow();
      tr.insertCell().textContent = label(r.date);
      var who = r.people.join(", ");
      if (r.short) {
        short++;
        tr.className = "short";
        who += (who ? ", " : "") + "need " + r.short + " more";
      }
      tr.insertCell().textContent = who;
    });
    resultBox.appendChild(t);

    var t2 = document.createElement("table");
    t2.createCaption().textContent = "Turns each";
    var h2 = t2.createTHead().insertRow();
    ["Name", "Turns", "Days away"].forEach(function (x) {
      var th = document.createElement("th"); th.scope = "col"; th.textContent = x; h2.appendChild(th);
    });
    var b2 = t2.createTBody();
    rota.people.forEach(function (n) {
      var tr = b2.insertRow();
      tr.insertCell().textContent = n;
      tr.insertCell().textContent = rota.count[n];
      var a = 0;
      rota.rows.forEach(function (r) { if (away[n] && away[n][r.date]) a++; });
      tr.insertCell().textContent = a;
    });
    t2.style.marginTop = "1rem";
    resultBox.appendChild(t2);

    if (short) {
      var w = document.createElement("p");
      w.className = "warn";
      w.textContent = short + (short === 1 ? " day doesn't" : " days don't") +
        " have enough people. Ask someone to swap, or add names.";
      resultBox.appendChild(w);
    }
    outButtons.hidden = false;
    lastRota = rota;
  }

  // ---- output ----
  function asText(rota) {
    return rota.rows.map(function (r) {
      return label(r.date) + ": " + (r.people.join(", ") || "-") +
        (r.short ? " (need " + r.short + " more)" : "");
    }).join("\n");
  }
  function csvCell(s) { return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }
  function asCsv(rota) {
    var head = ["Date"];
    for (var i = 1; i <= rota.slots; i++) head.push("Person " + i);
    var lines = [head.join(",")];
    rota.rows.forEach(function (r) {
      var cells = [r.date];
      for (var i = 0; i < rota.slots; i++) cells.push(csvCell(r.people[i] || ""));
      lines.push(cells.join(","));
    });
    return lines.join("\r\n");
  }

  // ---- wiring ----
  function refresh() { drawAway(); save(); }

  DAY_NAMES.forEach(function (n, i) {
    var span = document.createElement("span");
    var c = document.createElement("input");
    c.type = "checkbox"; c.id = "day-" + i; c.value = i;
    c.addEventListener("change", refresh);
    var l = document.createElement("label");
    l.htmlFor = c.id; l.textContent = n;
    span.appendChild(c); span.appendChild(l);
    daysBox.appendChild(span);
  });

  var s = load();
  if (s) {
    peopleBox.value = s.people || "";
    startBox.value = s.start || "";
    endBox.value = s.end || "";
    slotsBox.value = s.slots || 1;
    avoidBox.checked = s.avoid !== false;
    away = s.away || {};
    seed = s.seed || 1;
    (s.days || []).forEach(function (i) { var c = el("day-" + i); if (c) c.checked = true; });
  } else {
    // First visit: a filled-in example, so the result is visible before anyone types.
    var today = new Date();
    var t0 = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()));
    startBox.value = iso(t0);
    endBox.value = iso(new Date(t0.getTime() + 8 * 7 * 864e5));
    el("day-0").checked = true;
    peopleBox.value = "Ana\nBen\nChris\nDee\nEli";
    slotsBox.value = 2;
    var sundays = dates();
    away = {};
    if (sundays[1]) away.Ana = {}, away.Ana[sundays[1]] = true;
    if (sundays[2]) away.Dee = {}, away.Dee[sundays[2]] = true;
    if (sundays[4]) away.Ben = {}, away.Ben[sundays[4]] = true;
    isExample = true;
  }

  [peopleBox, startBox, endBox].forEach(function (x) { x.addEventListener("change", refresh); });
  [slotsBox, avoidBox].forEach(function (x) { x.addEventListener("change", save); });

  el("make").addEventListener("click", function () { show(make()); save(); });
  el("shuffle").addEventListener("click", function () {
    seed = (seed * 48271) % 2147483647 || 1;
    show(make()); save();
  });
  el("print").addEventListener("click", function () { window.print(); });
  el("copy").addEventListener("click", function () {
    if (!lastRota) return;
    var text = asText(lastRota);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { statusBox.textContent = "Copied. Paste it into a message or email."; },
        function () { statusBox.textContent = "Copy didn't work here. Try Print instead."; }
      );
    } else {
      statusBox.textContent = "Copy didn't work here. Try Print instead.";
    }
  });
  el("csv").addEventListener("click", function () {
    if (!lastRota) return;
    var blob = new Blob([asCsv(lastRota)], { type: "text/csv" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "volunteer-schedule.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    statusBox.textContent = "Saved volunteer-schedule.csv. It opens in Excel or any spreadsheet.";
  });
  el("clear").addEventListener("click", function () {
    if (!window.confirm("Clear all names, days and away marks?")) return;
    var today = new Date();
    var t0 = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()));
    startBox.value = iso(t0);
    endBox.value = iso(new Date(t0.getTime() + 12 * 7 * 864e5));
    daysBox.querySelectorAll("input").forEach(function (c) { c.checked = c.value === "0"; });
    slotsBox.value = 1;
    avoidBox.checked = true;
    seed = 1;
    startFresh();
  });

  // Empties the page and saves the empty state, so a reload never brings the example back.
  function startFresh() {
    peopleBox.value = "";
    away = {};
    isExample = false;
    el("example-note").hidden = true;
    resultBox.textContent = "";
    statusBox.textContent = "";
    outButtons.hidden = true;
    lastRota = null;
    drawAway();
    save();
    peopleBox.focus();
  }
  el("fresh").addEventListener("click", startFresh);
  [peopleBox, startBox, endBox, slotsBox].forEach(function (x) {
    x.addEventListener("input", function () { if (isExample) { isExample = false; el("example-note").hidden = true; } });
  });

  drawAway();
  if (isExample) { show(make()); } else { el("example-note").hidden = true; }
})();
