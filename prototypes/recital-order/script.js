// Recital order maker. Runs only in this browser; saves to localStorage.
(function () {
  "use strict";

  var KEY = "recital-order-v1";
  var MAX_LINES = 200;
  var EXAMPLE = [
    "Opening Number: Zoe, Hannah, Leo, Isabel",
    "Tiny Tots Ballet: Sophie, Luna, Ella",
    "Junior Tap: Ava, Mia, Grace",
    "Teen Lyrical: Zoe, Lily, Emma",
    "Mini Hip Hop: Luna, Leo, Ella",
    "Junior Jazz: Ava, Mia, Chloe, Ruby",
    "Senior Contemporary: Emma, Hannah, Isabel",
    "Teen Hip Hop: Zoe, Noah, Ethan, Lily",
    "Junior Ballet: Grace, Chloe, Ruby, Sophie",
    "Ava and Mia Duet: Ava, Mia",
    "Senior Tap: Hannah, Isabel, Noah",
    "Boys Breakdance: Noah, Ethan, Leo",
    "Emma Solo: Emma",
    "Finale: Ava, Zoe, Emma, Hannah, Noah"
  ].join("\n");

  var el = function (id) { return document.getElementById(id); };
  var listBox = el("list"), gapBox = el("gap"), pinFirstBox = el("pin-first"), pinLastBox = el("pin-last");
  var summaryBox = el("summary"), resultBox = el("result"), whoBox = el("who");
  var statusBox = el("status"), outButtons = el("out-buttons");

  var order = null; // order[k] = index of the line shown as number k + 1
  var show = null;  // the parsed list
  var undoState = null;

  // ---- reading the list ----
  function parse(text) {
    var routines = [], dancers = [], ids = {};
    text.split("\n").slice(0, MAX_LINES).forEach(function (line) {
      var raw = line.trim();
      if (!raw) return;
      var colon = raw.indexOf(":");
      var name = (colon === -1 ? raw : raw.slice(0, colon)).trim() || "Untitled";
      var who = [];
      if (colon !== -1) {
        raw.slice(colon + 1).split(",").forEach(function (n) {
          n = n.trim();
          if (!n) return;
          var k = n.toLowerCase();
          if (!(k in ids)) { ids[k] = dancers.length; dancers.push(n); }
          if (who.indexOf(ids[k]) === -1) who.push(ids[k]);
        });
      }
      routines.push({ name: name, who: who });
    });
    return { routines: routines, dancers: dancers };
  }

  function gap() {
    var g = parseInt(gapBox.value, 10);
    if (isNaN(g)) g = 1;
    return Math.max(1, Math.min(10, g));
  }

  // ---- scoring an order ----
  // A dancer with b other numbers between two of theirs, when they need g, costs (g - b)^2.
  function penalty(between, g) { return between < g ? (g - between) * (g - between) : 0; }

  function cost(s, ord, g) {
    var last = new Array(s.dancers.length), c = 0;
    for (var k = 0; k < ord.length; k++) {
      var who = s.routines[ord[k]].who;
      for (var i = 0; i < who.length; i++) {
        var d = who[i];
        if (last[d] !== undefined) c += penalty(k - last[d] - 1, g);
        last[d] = k;
      }
    }
    return c;
  }

  // Every place a dancer has fewer numbers between than asked.
  function tightSpots(s, ord, g) {
    var last = new Array(s.dancers.length), out = [];
    ord.forEach(function (r, k) {
      s.routines[r].who.forEach(function (d) {
        if (last[d] !== undefined && k - last[d] - 1 < g) {
          out.push({ dancer: d, a: last[d], b: k, between: k - last[d] - 1 });
        }
        last[d] = k;
      });
    });
    return out;
  }

  // ---- making an order ----
  function bounds(n, pinFirst, pinLast) {
    var lo = pinFirst ? 1 : 0;
    var hi = pinLast && n > 1 ? n - 2 : n - 1;
    return { lo: lo, hi: hi };
  }

  // Fill the free places one at a time, each time with the number that fits best there.
  function greedy(s, g, pinFirst, pinLast) {
    var n = s.routines.length, b = bounds(n, pinFirst, pinLast);
    var ord = new Array(n), last = new Array(s.dancers.length), left = [];
    var inFinale = {};
    if (pinFirst) ord[0] = 0;
    if (pinLast && n > 1) {
      ord[n - 1] = n - 1;
      s.routines[n - 1].who.forEach(function (d) { inFinale[d] = true; });
    }
    for (var r = 0; r < n; r++) {
      if (!(pinFirst && r === 0) && !(pinLast && n > 1 && r === n - 1)) left.push(r);
    }
    if (pinFirst) s.routines[0].who.forEach(function (d) { last[d] = 0; });
    for (var k = b.lo; k <= b.hi; k++) {
      var best = -1, bestScore = Infinity;
      for (var i = 0; i < left.length; i++) {
        var who = s.routines[left[i]].who, score = Math.random() * 0.5;
        for (var j = 0; j < who.length; j++) {
          var d = who[j];
          if (last[d] !== undefined) score += penalty(k - last[d] - 1, g);
          if (inFinale[d]) score += penalty(n - 1 - k - 1, g);
        }
        if (score < bestScore) { bestScore = score; best = i; }
      }
      var pick = left.splice(best, 1)[0];
      ord[k] = pick;
      s.routines[pick].who.forEach(function (d) { last[d] = k; });
    }
    return ord;
  }

  // Then keep swapping or moving numbers while it doesn't get worse. Restart until it is
  // perfect or time is up, and keep the best order found.
  function arrange(s, g, pinFirst, pinLast) {
    var n = s.routines.length;
    if (!n) return [];
    var b = bounds(n, pinFirst, pinLast), span = b.hi - b.lo + 1;
    var best = null, bestCost = Infinity, until = Date.now() + 400;
    do {
      var ord = greedy(s, g, pinFirst, pinLast), c = cost(s, ord, g);
      for (var it = 0; it < 6000 && c > 0 && span > 1; it++) {
        var i = b.lo + Math.floor(Math.random() * span);
        var j = b.lo + Math.floor(Math.random() * span);
        if (i === j) continue;
        var before = ord.slice();
        if (Math.random() < 0.5) {
          var t = ord[i]; ord[i] = ord[j]; ord[j] = t;
        } else {
          ord.splice(j, 0, ord.splice(i, 1)[0]);
        }
        var c2 = cost(s, ord, g);
        if (c2 <= c) c = c2; else ord = before;
      }
      if (c < bestCost) { bestCost = c; best = ord; }
    } while (bestCost > 0 && Date.now() < until);
    return best;
  }

  function validOrder(o, n) {
    if (!Array.isArray(o) || o.length !== n) return false;
    var seen = {};
    for (var i = 0; i < n; i++) {
      if (typeof o[i] !== "number" || o[i] < 0 || o[i] >= n || seen[o[i]]) return false;
      seen[o[i]] = true;
    }
    return true;
  }

  // ---- showing it ----
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }

  function draw(focusId) {
    summaryBox.textContent = "";
    resultBox.textContent = "";
    whoBox.textContent = "";
    statusBox.textContent = "";
    if (!show || !show.routines.length || !order) {
      outButtons.hidden = true;
      var p = document.createElement("p");
      p.className = "hint";
      p.textContent = "Add your numbers in step 1 and the order appears here.";
      summaryBox.appendChild(p);
      return;
    }
    var g = gap(), tight = tightSpots(show, order, g);
    var tightAt = {};
    tight.forEach(function (t) { tightAt[t.b] = true; });

    var head = document.createElement("p");
    head.textContent = plural(show.routines.length, "number", "numbers") + ", " +
      plural(show.dancers.length, "dancer", "dancers") + ". ";
    var verdict = document.createElement("span");
    if (!tight.length) {
      verdict.className = "ok";
      verdict.textContent = "Every dancer has at least " + plural(g, "other number", "other numbers") +
        " between their own.";
    } else {
      verdict.className = "warn";
      verdict.textContent = plural(tight.length, "tight spot", "tight spots") +
        ": fewer than " + g + " numbers between.";
    }
    head.appendChild(verdict);
    summaryBox.appendChild(head);
    if (tight.length) {
      var ul = document.createElement("ul");
      tight.forEach(function (t) {
        var li = document.createElement("li");
        li.textContent = show.dancers[t.dancer] + ": #" + (t.a + 1) + " " + show.routines[order[t.a]].name +
          " and #" + (t.b + 1) + " " + show.routines[order[t.b]].name + ", " +
          (t.between === 0 ? "back to back" : plural(t.between, "number", "numbers") + " between");
        ul.appendChild(li);
      });
      summaryBox.appendChild(ul);
      var tip = document.createElement("p");
      tip.className = "hint";
      tip.textContent = "Try another order, ask for fewer numbers between, or move numbers by hand.";
      summaryBox.appendChild(tip);
    }

    order.forEach(function (r, k) {
      var rt = show.routines[r];
      var li = document.createElement("li");
      if (tightAt[k]) li.className = "tight";
      var num = document.createElement("span");
      num.className = "num";
      num.textContent = (k + 1) + ".";
      var what = document.createElement("span");
      what.className = "what";
      var name = document.createElement("span");
      name.className = "name";
      name.textContent = rt.name;
      var who = document.createElement("span");
      who.className = "who";
      who.textContent = rt.who.map(function (d) { return show.dancers[d]; }).join(", ") || "No dancers listed";
      what.appendChild(name);
      what.appendChild(who);
      if (tightAt[k]) {
        var flag = document.createElement("span");
        flag.className = "flag";
        flag.textContent = "Quick change: " + tight.filter(function (t) { return t.b === k; })
          .map(function (t) { return show.dancers[t.dancer]; }).join(", ");
        what.appendChild(flag);
      }
      var move = document.createElement("span");
      move.className = "move";
      move.appendChild(moveButton("up", k, rt.name, k === 0));
      move.appendChild(moveButton("down", k, rt.name, k === order.length - 1));
      li.appendChild(num);
      li.appendChild(what);
      li.appendChild(move);
      resultBox.appendChild(li);
    });

    drawWho(g);
    outButtons.hidden = false;
    if (focusId && el(focusId)) el(focusId).focus();
  }

  function moveButton(dir, k, name, off) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "secondary";
    b.id = dir + "-" + k;
    b.textContent = dir === "up" ? "↑" : "↓";
    b.setAttribute("aria-label", "Move " + name + (dir === "up" ? " earlier" : " later"));
    b.disabled = off;
    b.addEventListener("click", function () {
      var to = dir === "up" ? k - 1 : k + 1;
      var t = order[k]; order[k] = order[to]; order[to] = t;
      save();
      var id = dir + "-" + to;
      if (to === 0 || to === order.length - 1) id = (dir === "up" ? "down-" : "up-") + to;
      draw(id);
      statusBox.textContent = "Moved " + name + " to number " + (to + 1) + ".";
    });
    return b;
  }

  // Who dances when: one row per dancer, for the quick-change helpers backstage.
  function drawWho(g) {
    var at = show.dancers.map(function () { return []; });
    order.forEach(function (r, k) { show.routines[r].who.forEach(function (d) { at[d].push(k + 1); }); });
    var rows = show.dancers.map(function (n, d) {
      var fewest = null;
      for (var i = 1; i < at[d].length; i++) {
        var b = at[d][i] - at[d][i - 1] - 1;
        if (fewest === null || b < fewest) fewest = b;
      }
      return { name: n, at: at[d], fewest: fewest };
    });
    if (!rows.length) return;
    rows.sort(function (a, b) { return a.name.localeCompare(b.name); });
    var t = document.createElement("table");
    t.createCaption().textContent = "Who dances when";
    var h = t.createTHead().insertRow();
    ["Dancer", "Numbers", "Fewest between"].forEach(function (x) {
      var th = document.createElement("th"); th.scope = "col"; th.textContent = x; h.appendChild(th);
    });
    var body = t.createTBody();
    rows.forEach(function (row) {
      var tr = body.insertRow();
      if (row.fewest !== null && row.fewest < g) tr.className = "tight";
      tr.insertCell().textContent = row.name;
      tr.insertCell().textContent = row.at.map(function (k) { return "#" + k; }).join(", ");
      tr.insertCell().textContent = row.fewest === null ? "Only one number" :
        row.fewest === 0 ? "Back to back" : String(row.fewest);
    });
    whoBox.appendChild(t);
  }

  function asText() {
    return order.map(function (r, k) {
      var rt = show.routines[r];
      var who = rt.who.map(function (d) { return show.dancers[d]; }).join(", ");
      return (k + 1) + ". " + rt.name + (who ? " (" + who + ")" : "");
    }).join("\n");
  }

  // ---- saving ----
  function state() {
    return { list: listBox.value, gap: gapBox.value, pinFirst: pinFirstBox.checked,
      pinLast: pinLastBox.checked, order: order };
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state())); }
    catch (e) { /* private mode: work without saving */ }
  }
  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch (e) { return null; }
  }
  function apply(s) {
    listBox.value = s.list || "";
    gapBox.value = s.gap || 2;
    pinFirstBox.checked = s.pinFirst !== false;
    pinLastBox.checked = s.pinLast !== false;
    show = parse(listBox.value);
    order = validOrder(s.order, show.routines.length) ? s.order : null;
    if (!order && show.routines.length) order = arrange(show, gap(), pinFirstBox.checked, pinLastBox.checked);
    draw();
  }

  // ---- wiring ----
  function remake() {
    show = parse(listBox.value);
    order = show.routines.length ? arrange(show, gap(), pinFirstBox.checked, pinLastBox.checked) : null;
    draw();
    save();
  }
  function leaveExample() {
    el("example-note").hidden = true;
    el("cleared").hidden = true;
  }

  var timer = null;
  listBox.addEventListener("input", function () {
    leaveExample();
    clearTimeout(timer);
    timer = setTimeout(remake, 500);
  });
  gapBox.addEventListener("input", function () {
    leaveExample();
    clearTimeout(timer);
    timer = setTimeout(remake, 300);
  });
  gapBox.addEventListener("change", function () { gapBox.value = gap(); });
  [pinFirstBox, pinLastBox].forEach(function (x) {
    x.addEventListener("change", function () { leaveExample(); remake(); });
  });

  el("shuffle").addEventListener("click", function () {
    leaveExample();
    remake();
    statusBox.textContent = show.routines.length ? "Here is another order." : "";
  });
  el("print").addEventListener("click", function () { window.print(); });
  el("copy").addEventListener("click", function () {
    if (!order) return;
    var text = asText();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { statusBox.textContent = "Copied. Paste it into a message or a program."; },
        function () { statusBox.textContent = "Copy didn't work here. Try Print instead."; }
      );
    } else {
      statusBox.textContent = "Copy didn't work here. Try Print instead.";
    }
  });

  // No confirmation dialog (phones often block them): empty the page at once, offer Undo.
  // The empty state is saved, so a reload never brings the example back.
  el("fresh").addEventListener("click", function () {
    clearTimeout(timer);
    undoState = state();
    listBox.value = "";
    gapBox.value = 2;
    pinFirstBox.checked = true;
    pinLastBox.checked = true;
    show = parse("");
    order = null;
    el("example-note").hidden = true;
    draw();
    save();
    el("cleared").hidden = false;
    listBox.focus();
  });
  el("undo").addEventListener("click", function () {
    if (!undoState) return;
    apply(undoState);
    save();
    undoState = null;
    el("cleared").hidden = true;
    statusBox.textContent = "Your list is back.";
  });

  var saved = load();
  if (saved) {
    el("example-note").hidden = true;
    apply(saved);
  } else {
    // First visit: a filled-in example, so the result is visible before anyone types.
    apply({ list: EXAMPLE, gap: 2, pinFirst: true, pinLast: true, order: null });
  }
})();
