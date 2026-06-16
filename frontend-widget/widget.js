/*!
 * AI Chat Widget — embeddable, dependency-free.
 *
 * Usage:
 *   <script src="https://chat.example.com/widget.js"></script>
 *   <script>
 *     window.ChatWidget.init({ widgetId: "abc123" });
 *   </script>
 *
 * Options:
 *   widgetId   (required) — the widget id issued by the platform.
 *   apiBase    (optional) — API origin. Defaults to the origin that served
 *                            this script, so no config is needed in production.
 *   title      (optional) — header title text.
 *   lang       (optional) — "ar" forces RTL/Arabic UI strings, "en" forces LTR.
 *                            Defaults to the page <html lang> / browser.
 *   primary    (optional) — primary accent color (hex).
 */
(function () {
  "use strict";

  if (window.ChatWidget && window.ChatWidget.__loaded) return;

  // Derive the API base from this script's own URL.
  function scriptOrigin() {
    var cur = document.currentScript;
    if (cur && cur.src) {
      try { return new URL(cur.src).origin; } catch (e) {}
    }
    var scripts = document.getElementsByTagName("script");
    for (var i = scripts.length - 1; i >= 0; i--) {
      if (scripts[i].src && scripts[i].src.indexOf("widget.js") !== -1) {
        try { return new URL(scripts[i].src).origin; } catch (e) {}
      }
    }
    return window.location.origin;
  }

  var I18N = {
    en: {
      title: "Chat with us",
      placeholder: "Type your message…",
      send: "Send",
      greeting: "Hi! 👋 How can I help you today?",
      error: "Sorry, something went wrong. Please try again.",
      offline: "Connection problem. Please try again.",
      notFound: "No suitable answer was found.\nTry different keywords or send your question directly to the expert.",
      expertBtn: "Ask the expert",
    },
    ar: {
      title: "تحدث معنا",
      placeholder: "اكتب رسالتك…",
      send: "إرسال",
      greeting: "مرحباً! 👋 كيف يمكنني مساعدتك اليوم؟",
      error: "عذراً، حدث خطأ ما. حاول مرة أخرى.",
      offline: "مشكلة في الاتصال. حاول مرة أخرى.",
      notFound: "لم يتم العثور على إجابة مناسبة\nجرّب كلمات مختلفة أو أرسل استفسارك مباشرة إلى الخبير.",
      expertBtn: "أرسل استفسارك إلى الخبير",
    },
  };

  function detectLang(opt) {
    if (opt === "ar" || opt === "en") return opt;
    var htmlLang = (document.documentElement.lang || "").toLowerCase();
    var nav = (navigator.language || "").toLowerCase();
    if (htmlLang.indexOf("ar") === 0 || nav.indexOf("ar") === 0) return "ar";
    return "en";
  }

  function injectStyles(primary) {
    if (document.getElementById("cw-styles")) return;
    var css = `
.cw-root{position:fixed;z-index:2147483000;bottom:20px;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans Arabic",sans-serif;}
.cw-root.cw-ltr{right:20px;}
.cw-root.cw-rtl{left:20px;direction:rtl;}
.cw-btn{width:60px;height:60px;border-radius:50%;border:0;cursor:pointer;background:${primary};color:#fff;box-shadow:0 6px 20px rgba(0,0,0,.25);display:flex;align-items:center;justify-content:center;transition:transform .15s ease;}
.cw-btn:hover{transform:scale(1.06);}
.cw-btn svg{width:28px;height:28px;}
.cw-panel{position:absolute;bottom:76px;width:360px;max-width:calc(100vw - 32px);height:520px;max-height:calc(100vh - 120px);background:#fff;border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,.28);display:none;flex-direction:column;overflow:hidden;}
.cw-root.cw-ltr .cw-panel{right:0;}
.cw-root.cw-rtl .cw-panel{left:0;}
.cw-open .cw-panel{display:flex;}
.cw-header{background:${primary};color:#fff;padding:16px 18px;font-weight:600;font-size:16px;display:flex;align-items:center;justify-content:space-between;}
.cw-title{display:flex;align-items:center;gap:8px;}
.cw-logo{width:24px;height:24px;border-radius:50%;object-fit:cover;background:#fff;}
.cw-close{background:transparent;border:0;color:#fff;cursor:pointer;font-size:20px;line-height:1;padding:4px;}
.cw-body{flex:1;overflow-y:auto;padding:16px;background:#f6f7f9;display:flex;flex-direction:column;gap:10px;}
.cw-msg{max-width:80%;padding:10px 13px;border-radius:14px;font-size:14px;line-height:1.45;word-wrap:break-word;white-space:pre-wrap;}
.cw-msg.cw-user{align-self:flex-end;background:${primary};color:#fff;border-bottom-right-radius:4px;}
.cw-root.cw-rtl .cw-msg.cw-user{border-bottom-right-radius:14px;border-bottom-left-radius:4px;}
.cw-msg.cw-bot{align-self:flex-start;background:#fff;color:#1f2937;border:1px solid #e5e7eb;border-bottom-left-radius:4px;}
.cw-root.cw-rtl .cw-msg.cw-bot{border-bottom-left-radius:14px;border-bottom-right-radius:4px;}
.cw-typing{align-self:flex-start;background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:12px 14px;display:flex;gap:4px;}
.cw-typing span{width:7px;height:7px;border-radius:50%;background:#9ca3af;animation:cw-bounce 1.2s infinite ease-in-out;}
.cw-typing span:nth-child(2){animation-delay:.15s;}
.cw-typing span:nth-child(3){animation-delay:.3s;}
@keyframes cw-bounce{0%,60%,100%{transform:translateY(0);opacity:.5;}30%{transform:translateY(-6px);opacity:1;}}
.cw-footer{display:flex;gap:8px;padding:12px;border-top:1px solid #e5e7eb;background:#fff;align-items:flex-end;}
.cw-input{flex:1;border:1px solid #d1d5db;border-radius:10px;padding:10px 12px;font-size:14px;outline:none;font-family:inherit;line-height:1.4;resize:none;max-height:120px;overflow-y:auto;}
.cw-input:focus{border-color:${primary};}
.cw-send{background:${primary};color:#fff;border:0;border-radius:10px;padding:10px 16px;cursor:pointer;font-weight:600;font-size:14px;white-space:nowrap;}
.cw-send:disabled{opacity:.5;cursor:not-allowed;}
.cw-expert-btn{margin-top:4px;background:${primary};color:#fff;border:0;border-radius:10px;padding:9px 14px;cursor:pointer;font-weight:600;font-size:13px;font-family:inherit;align-self:flex-start;}
.cw-root.cw-rtl .cw-expert-btn{align-self:flex-end;}
.cw-expert-btn:hover{filter:brightness(1.08);}
@media (max-width:480px){
  .cw-panel{width:calc(100vw - 24px);height:calc(100vh - 100px);}
  .cw-root{bottom:14px;}
  .cw-root.cw-ltr{right:12px;}
  .cw-root.cw-rtl{left:12px;}
}`;
    var style = document.createElement("style");
    style.id = "cw-styles";
    style.textContent = css;
    document.head.appendChild(style);
  }

  function sessionId(widgetId) {
    var key = "cw_session_" + widgetId;
    var sid = null;
    try { sid = localStorage.getItem(key); } catch (e) {}
    if (!sid) {
      sid = "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      try { localStorage.setItem(key, sid); } catch (e) {}
    }
    return sid;
  }

  var ICON_CHAT =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>';

  function ChatWidget() {
    this.__loaded = true;
  }

  function pick(a, b) {
    return a !== undefined && a !== null ? a : b;
  }

  ChatWidget.prototype.init = function (opts) {
    opts = opts || {};
    if (!opts.widgetId) {
      console.error("[ChatWidget] init() requires a widgetId.");
      return;
    }
    var self = this;
    var apiBase = (opts.apiBase || scriptOrigin()).replace(/\/$/, "");

    // Load server-managed config (set in the admin panel), then render.
    // Explicit init() options always take precedence over server values.
    fetch(apiBase + "/api/widget/" + encodeURIComponent(opts.widgetId) + "/config")
      .then(function (r) { return r.ok ? r.json() : {}; })
      .catch(function () { return {}; })
      .then(function (cfg) {
        cfg = cfg || {};
        self._render({
          widgetId: opts.widgetId,
          apiBase: apiBase,
          title: pick(opts.title, cfg.title),
          primary: pick(opts.primary, cfg.primary),
          greeting: pick(opts.greeting, cfg.greeting),
          logoUrl: pick(opts.logoUrl, cfg.logo_url),
          lang: pick(opts.lang, cfg.lang),
          notFoundMessage: pick(opts.notFoundMessage, cfg.not_found_message),
          expertButtonText: pick(opts.expertButtonText, cfg.expert_button_text),
          expertUrl: pick(opts.expertUrl, cfg.expert_url),
          expertSelector: pick(opts.expertSelector, cfg.expert_selector),
        });
      });
  };

  ChatWidget.prototype._render = function (opts) {
    var self = this;
    var apiBase = opts.apiBase;
    var lang = detectLang(opts.lang);
    var t = I18N[lang];
    var primary = opts.primary || "#6366f1";
    var sid = sessionId(opts.widgetId);
    var busy = false;

    injectStyles(primary);

    var root = document.createElement("div");
    root.className = "cw-root " + (lang === "ar" ? "cw-rtl" : "cw-ltr");
    root.innerHTML =
      '<div class="cw-panel" role="dialog" aria-label="Chat">' +
        '<div class="cw-header"><span class="cw-title">' +
          (opts.logoUrl ? '<img class="cw-logo" src="' + escapeHtml(opts.logoUrl) + '" alt="" />' : '') +
          escapeHtml(opts.title || t.title) + '</span>' +
          '<button class="cw-close" aria-label="Close">×</button></div>' +
        '<div class="cw-body"></div>' +
        '<div class="cw-footer">' +
          '<textarea class="cw-input" rows="1" placeholder="' + escapeHtml(t.placeholder) + '"></textarea>' +
          '<button class="cw-send">' + escapeHtml(t.send) + '</button>' +
        '</div>' +
      '</div>' +
      '<button class="cw-btn" aria-label="Open chat">' + ICON_CHAT + '</button>';
    document.body.appendChild(root);

    var btn = root.querySelector(".cw-btn");
    var panel = root.querySelector(".cw-panel");
    var body = root.querySelector(".cw-body");
    var input = root.querySelector(".cw-input");
    var sendBtn = root.querySelector(".cw-send");
    var closeBtn = root.querySelector(".cw-close");
    var greeted = false;

    function addMsg(text, who) {
      var el = document.createElement("div");
      el.className = "cw-msg " + (who === "user" ? "cw-user" : "cw-bot");
      el.textContent = text;
      body.appendChild(el);
      body.scrollTop = body.scrollHeight;
      return el;
    }

    function showTyping() {
      var el = document.createElement("div");
      el.className = "cw-typing";
      el.innerHTML = "<span></span><span></span><span></span>";
      body.appendChild(el);
      body.scrollTop = body.scrollHeight;
      return el;
    }

    // Shown when the backend reports the answer was not in the knowledge base.
    // Renders the configurable "no answer" message plus a button that triggers
    // the host page's expert element (default selector: "#emptyState > button").
    function addExpertButton() {
      var wrap = document.createElement("div");
      wrap.className = "cw-msg cw-bot";
      wrap.style.background = "transparent";
      wrap.style.border = "0";
      wrap.style.padding = "0";
      var b = document.createElement("button");
      b.className = "cw-expert-btn";
      b.textContent = opts.expertButtonText || t.expertBtn;
      b.addEventListener("click", function () {
        // 1) Preferred: open a configured link (WhatsApp / email / contact page).
        if (opts.expertUrl) {
          window.open(opts.expertUrl, "_blank", "noopener");
          return;
        }
        // 2) Fallback: click an existing element on the host page. Defaults to
        // the Bootstrap "Ask the expert" modal trigger; override via admin.
        var selector = opts.expertSelector || '[data-bs-target="#askExpertModal"]';
        var el = document.querySelector(selector);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.click();
        } else {
          console.warn("[ChatWidget] expert: no expertUrl and selector not found:", selector);
        }
      });
      wrap.appendChild(b);
      body.appendChild(wrap);
      body.scrollTop = body.scrollHeight;
    }

    function toggle(open) {
      var willOpen = open === undefined ? !root.classList.contains("cw-open") : open;
      root.classList.toggle("cw-open", willOpen);
      if (willOpen) {
        if (!greeted) { addMsg(opts.greeting || t.greeting, "bot"); greeted = true; }
        setTimeout(function () { input.focus(); }, 50);
      }
    }

    function send() {
      var text = (input.value || "").trim();
      if (!text || busy) return;
      busy = true;
      sendBtn.disabled = true;
      addMsg(text, "user");
      input.value = "";
      autoGrow();
      var typing = showTyping();

      fetch(apiBase + "/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          widget_id: opts.widgetId,
          session_id: sid,
          message: text,
        }),
      })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(function (data) {
          typing.remove();
          if (data && data.found === false) {
            // No answer in the knowledge base: custom message + expert button.
            addMsg(opts.notFoundMessage || t.notFound, "bot");
            addExpertButton();
          } else {
            addMsg((data && data.answer) || t.error, "bot");
          }
        })
        .catch(function (err) {
          typing.remove();
          console.error("[ChatWidget]", err);
          addMsg(t.offline, "bot");
        })
        .finally(function () {
          busy = false;
          sendBtn.disabled = false;
          input.focus();
        });
    }

    // Grow the textarea with its content, up to the CSS max-height.
    function autoGrow() {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 120) + "px";
    }

    btn.addEventListener("click", function () { toggle(); });
    closeBtn.addEventListener("click", function () { toggle(false); });
    sendBtn.addEventListener("click", send);
    input.addEventListener("input", autoGrow);
    input.addEventListener("keydown", function (e) {
      // Enter sends; Shift+Enter inserts a newline.
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
    });

    self.open = function () { toggle(true); };
    self.close = function () { toggle(false); };
  };

  // Shared HTML escaper, used when building markup from option strings.
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  window.ChatWidget = new ChatWidget();
})();
