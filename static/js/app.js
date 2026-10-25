/* KamKarao front-end behaviour. Plain JS + htmx, no build step. */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Bottom sheet / dialog ---------- */
  const Sheet = {
    el: null, body: null, lastFocus: null,
    init() {
      this.el = $("#sheet");
      this.body = $("#sheet-body");
      if (!this.el) return;
      this.el.addEventListener("click", (e) => {
        if (e.target.closest("[data-sheet-close]")) this.close();
      });
      document.addEventListener("keydown", (e) => { if (e.key === "Escape" && this.isOpen()) this.close(); });
    },
    isOpen() { return this.el && this.el.classList.contains("open"); },
    open() {
      if (!this.el) return;
      if (!this.isOpen()) this.lastFocus = document.activeElement;
      this.el.classList.add("open");
      this.el.setAttribute("aria-hidden", "false");
      document.documentElement.style.overflow = "hidden";
      setTimeout(() => {
        const f = $("input:not([type=hidden]), button, a[href]", this.body);
        if (f && window.innerWidth >= 700) f.focus({ preventScroll: true });
      }, 60);
    },
    close() {
      if (!this.el) return;
      this.el.classList.remove("open");
      this.el.setAttribute("aria-hidden", "true");
      document.documentElement.style.overflow = "";
      if (this.lastFocus) this.lastFocus.focus({ preventScroll: true });
    },
    load(url) {
      if (window.htmx) htmx.ajax("GET", url, { target: "#sheet-body", swap: "innerHTML" });
    },
  };
  window.KKSheet = Sheet;

  document.addEventListener("htmx:afterSwap", (e) => {
    if (e.detail.target && e.detail.target.id === "sheet-body") Sheet.open();
    initReveal(e.detail.target);
    initOtp(e.detail.target);
  });
  document.addEventListener("htmx:responseError", () => toast(document.body.dataset.errorText || "Something went wrong"));
  document.addEventListener("htmx:sendError", () => toast(document.body.dataset.offlineText || "No internet connection"));

  /* ---------- Scroll reveal ---------- */
  let io = null;
  function initReveal(root = document) {
    const els = $$(".reveal:not(.in)", root);
    if (reduceMotion || !("IntersectionObserver" in window)) { els.forEach((el) => el.classList.add("in")); return; }
    if (!io) {
      io = new IntersectionObserver((entries) => {
        entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
      }, { rootMargin: "0px 0px -40px 0px", threshold: 0.08 });
    }
    els.forEach((el) => io.observe(el));
  }

  /* ---------- Count-up numbers ---------- */
  function initCounters() {
    $$("[data-count]").forEach((el) => {
      const target = parseInt(el.dataset.count, 10) || 0;
      if (reduceMotion || target < 2) { el.textContent = target; return; }
      const start = performance.now(), dur = 1200;
      const step = (t) => {
        const p = Math.min(1, (t - start) / dur);
        el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }

  /* ---------- Rotating search placeholder ---------- */
  function initSearchHints() {
    const input = $("[data-hints]");
    if (!input) return;
    let hints = [];
    try { hints = JSON.parse(input.dataset.hints); } catch (e) { return; }
    if (!hints.length || reduceMotion) return;
    let i = 0;
    setInterval(() => {
      if (document.activeElement === input || input.value) return;
      i = (i + 1) % hints.length;
      input.setAttribute("placeholder", hints[i]);
    }, 2600);
  }

  /* ---------- "Use my location" → nearest mohalla ---------- */
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-locate]");
    if (!btn) return;
    const msg = $("[data-locate-msg]");
    if (!navigator.geolocation) { if (msg) msg.textContent = btn.dataset.unsupported; return; }
    btn.disabled = true;
    if (msg) msg.textContent = btn.dataset.finding;
    navigator.geolocation.getCurrentPosition(async (pos) => {
      try {
        const r = await fetch(`${btn.dataset.url}?lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`);
        const data = await r.json();
        if (!r.ok) throw new Error(data.error);
        const pick = $(`[data-area-id="${data.id}"]`);
        if (pick) { pick.scrollIntoView({ block: "center", behavior: "smooth" }); pick.classList.add("is-on"); }
        if (msg) msg.textContent = `${btn.dataset.found} ${data.name} (${data.km} km)`;
        if (pick) setTimeout(() => pick.click(), 700);
      } catch (err) {
        if (msg) msg.textContent = btn.dataset.outside;
      } finally { btn.disabled = false; }
    }, () => { btn.disabled = false; if (msg) msg.textContent = btn.dataset.denied; },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
  });

  /* ---------- OTP box: digits only, auto-submit at 4 ---------- */
  function initOtp(root = document) {
    const box = $("[data-otp]", root);
    if (!box) return;
    box.addEventListener("input", () => {
      box.value = box.value.replace(/\D/g, "").slice(0, 4);
      if (box.value.length === 4) box.form.requestSubmit();
    });
    if ("OTPCredential" in window) {
      const ac = new AbortController();
      navigator.credentials.get({ otp: { transport: ["sms"] }, signal: ac.signal })
        .then((otp) => { if (otp && otp.code) { box.value = otp.code; box.form.requestSubmit(); } }).catch(() => {});
    }
  }

  /* ---------- Toasts ---------- */
  function toast(text) {
    let wrap = $(".toast-wrap");
    if (!wrap) { wrap = document.createElement("div"); wrap.className = "toast-wrap"; wrap.setAttribute("role", "status"); document.body.appendChild(wrap); }
    const t = document.createElement("div");
    t.className = "toast"; t.textContent = text; wrap.appendChild(t);
    setTimeout(() => t.remove(), 5200);
  }
  window.KKToast = toast;

  /* ---------- Open the number automatically after login ---------- */
  function resumeReveal() {
    const url = new URL(window.location.href);
    const id = url.searchParams.get("reveal");
    if (!id || !/^\d+$/.test(id)) return;
    const mode = url.searchParams.get("mode") === "wa" ? "wa" : "call";
    url.searchParams.delete("reveal"); url.searchParams.delete("mode");
    history.replaceState(null, "", url.pathname + url.search + url.hash);
    Sheet.load(`${document.body.dataset.langPrefix}/p/${id}/reveal/?mode=${mode}`);
  }

  /* ---------- Copy number ---------- */
  document.addEventListener("click", async (e) => {
    const b = e.target.closest("[data-copy]");
    if (!b) return;
    try { await navigator.clipboard.writeText(b.dataset.copy); toast(b.dataset.done || "Copied"); } catch (err) {}
  });

  /* ---------- Language switch keeps you on the same page ---------- */
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-lang]");
    if (!b) return;
    const form = $("#lang-form");
    form.language.value = b.dataset.lang;
    form.next.value = location.pathname + location.search;  // the URL as it is now, after htmx updates
    form.submit();
  });

  /* ---------- Boot ---------- */
  document.addEventListener("DOMContentLoaded", () => {
    Sheet.init();
    initReveal();
    initCounters();
    initSearchHints();
    resumeReveal();
    if (new URLSearchParams(location.search).get("login") === "1") Sheet.load(document.body.dataset.loginUrl);
    $$("[data-toast]").forEach((el) => toast(el.dataset.toast));
    if ($(".sticky-contact.mobile-bar")) document.body.classList.add("has-contact-bar");
    if ("serviceWorker" in navigator && location.protocol === "https:") navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
})();
