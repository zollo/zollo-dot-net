/* zollo.net: theme toggle, menu, hero typing, active nav link, and a tiny terminal. */
(function () {
  "use strict";
  var root = document.documentElement;
  root.classList.add("js");
  var reduceMotion = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  function store(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* private mode etc. */ }
  }

  /* theme */
  var toggle = document.querySelector(".theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      store("theme", next);
    });
  }

  /* mobile menu */
  var menuBtn = document.querySelector(".menu-btn");
  var links = document.getElementById("nav-links");
  if (menuBtn && links) {
    menuBtn.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", String(open));
    });
    links.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        links.classList.remove("open");
        menuBtn.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* 404 page: echo the path that was asked for */
  var missing = document.getElementById("missing-path");
  if (missing) missing.textContent = location.pathname;

  /* hero: type `whoami`, then reveal the output lines */
  var typed = document.querySelector(".hero .typed");
  var lines = document.querySelectorAll(".hero [data-line]");
  function showLines() {
    lines.forEach(function (l, i) {
      setTimeout(function () { l.classList.add("shown"); }, reduceMotion ? 0 : 180 * i);
    });
  }
  if (typed && !reduceMotion) {
    var word = typed.getAttribute("data-type") || typed.textContent;
    typed.textContent = "";
    var i = 0;
    (function tick() {
      typed.textContent = word.slice(0, ++i);
      if (i < word.length) setTimeout(tick, 90 + Math.random() * 60);
      else setTimeout(showLines, 250);
    })();
  } else {
    showLines();
  }

  /* highlight the nav link of the section on screen */
  var navLinks = document.querySelectorAll(".nav-links a[href^='#']");
  if ("IntersectionObserver" in window && navLinks.length) {
    var byId = {};
    navLinks.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        navLinks.forEach(function (a) { a.classList.remove("active"); });
        var a = byId[en.target.id];
        if (a) a.classList.add("active");
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    Object.keys(byId).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) io.observe(el);
    });
  }

  /* the contact terminal */
  var term = document.querySelector(".term-live");
  if (!term) return;
  var out = term.querySelector(".term-out");
  var form = term.querySelector(".term-form");
  var input = term.querySelector(".term-input");
  var scroller = term.querySelector(".term-scroll");
  var email = term.getAttribute("data-email");
  var github = term.getAttribute("data-github");
  var history = [];
  var hIndex = 0;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function print(text, cls) { out.appendChild(el("span", cls || "out", text)); }
  function link(label, href) {
    var line = el("span", "out");
    var a = el("a", null, label);
    a.href = href;
    if (href.indexOf("http") === 0) a.rel = "noopener";
    line.appendChild(a);
    out.appendChild(line);
  }
  function go(id) {
    var target = document.getElementById(id);
    if (target) target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
  }

  var commands = {
    help: function () {
      print("available commands:");
      print("  whoami     who is this guy?");
      print("  projects   list my open-source projects");
      print("  homelab    what's in the rack");
      print("  contact    how to reach me");
      print("  github     open my GitHub");
      print("  cd <name>  jump to a section (about, experience, projects, homelab, skills)");
      print("  theme      switch light/dark");
      print("  clear      clear the screen");
    },
    whoami: function () {
      print("joe zollo. staff engineer @ omnissa.");
      print("i automate infrastructure so nobody has to click through it twice.");
    },
    projects: function () {
      document.querySelectorAll("#projects .card h3 a").forEach(function (a) {
        link(a.textContent.trim(), a.href);
      });
    },
    ls: function () { commands.projects(); },
    homelab: function () {
      document.querySelectorAll("#homelab .rack-unit").forEach(function (u, i) {
        print("U" + (i + 1) + "  " + u.querySelector("strong").textContent, "hi");
      });
      print("all systems nominal. probably.");
    },
    contact: function () {
      link("mail: " + email, "mailto:" + email);
      link("code: " + github.replace("https://", ""), github);
    },
    github: function () { window.open(github, "_blank", "noopener"); print("opening " + github + " ..."); },
    theme: function () { if (toggle) toggle.click(); print("theme: " + root.getAttribute("data-theme")); },
    clear: function () { out.textContent = ""; },
    cd: function (args) {
      var id = (args[0] || "").replace(/[^a-z]/gi, "").toLowerCase();
      if (!id || id === "~" ) { window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" }); return; }
      if (document.getElementById(id)) { go(id); print("cd " + id); }
      else print("cd: " + args[0] + ": No such file or directory", "err");
    },
    sudo: function (args) {
      if (args.join(" ").indexOf("hire") !== -1) {
        print("[sudo] password for recruiter: ********");
        print("access granted. opening a draft email...", "hi");
        setTimeout(function () { location.href = "mailto:" + email + "?subject=Let's%20talk"; }, 700);
      } else {
        print("nice try. this incident will be reported.", "err");
      }
    },
    exit: function () { print("there is no escape. but there is a 'contact' command."); },
    rm: function () { print("rm: permission denied. backups are tested, too.", "err"); },
    uptime: function () { print("up 20 years, load average: coffee, coffee, coffee"); }
  };

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var raw = input.value.trim();
    input.value = "";
    var line = el("span");
    line.appendChild(el("span", "ps1", "$ "));
    line.appendChild(document.createTextNode(raw));
    out.appendChild(line);
    if (raw) {
      history.push(raw);
      hIndex = history.length;
      var parts = raw.split(/\s+/);
      var cmd = commands[parts[0].toLowerCase()];
      if (cmd) cmd(parts.slice(1));
      else print(parts[0] + ": command not found. try 'help'", "err");
    }
    scroller.scrollTop = scroller.scrollHeight;
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "ArrowUp" && hIndex > 0) { input.value = history[--hIndex]; e.preventDefault(); }
    else if (e.key === "ArrowDown") {
      hIndex = Math.min(history.length, hIndex + 1);
      input.value = history[hIndex] || "";
      e.preventDefault();
    } else if (e.key === "Tab") {
      var partial = input.value.toLowerCase();
      var match = Object.keys(commands).filter(function (c) { return partial && c.indexOf(partial) === 0; });
      if (match.length === 1) { input.value = match[0] + " "; e.preventDefault(); }
    }
  });

  term.addEventListener("click", function (e) {
    if (e.target.tagName !== "A") input.focus({ preventScroll: true });
  });
})();
