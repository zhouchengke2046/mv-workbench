/* MV 工作台服务版 Key 配置 UI（只在本地服务注入；file:// 静态版不加载） */
(() => {
  const $ = (id) => document.getElementById(id);
  let modal = null;

  function setStatus(text, isError) {
    const el = $("kc-status");
    if (!el) return;
    el.textContent = text || "";
    el.className = "kc-status" + (isError ? " err" : "");
  }

  async function api(url, options) {
    const res = await fetch(url, options);
    let data = {};
    try {
      data = await res.json();
    } catch (e) {
      /* ignore non-JSON */
    }
    if (!res.ok || data.ok === false) {
      throw new Error(data.error || ("HTTP " + res.status));
    }
    return data;
  }

  function ensureModal() {
    if (modal) return;
    const style = document.createElement("style");
    style.textContent = `
      .kc-backdrop{position:fixed;inset:0;background:rgba(29,33,41,.38);display:flex;
        align-items:center;justify-content:center;z-index:9999;padding:20px}
      .kc-backdrop[hidden]{display:none}
      .kc-card{width:min(460px,94vw);max-height:88vh;overflow:auto;background:#fff;
        border-radius:18px;box-shadow:0 24px 64px rgba(29,33,41,.24);padding:22px 24px}
      .kc-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:14px}
      .kc-title{font-size:17px;font-weight:600}
      .kc-sub{font-size:11px;color:var(--dim);margin-top:3px;line-height:1.5}
      .kc-x{border:0;background:transparent;font-size:22px;line-height:1;color:var(--dim);cursor:pointer;padding:0 2px}
      .kc-section{border-top:1px solid var(--line2);padding-top:12px;margin-top:12px}
      .kc-section-title{font-size:12px;font-weight:600;margin-bottom:8px;display:flex;gap:8px;align-items:center}
      .kc-mask{font-weight:400;color:var(--dim);font-size:11px}
      .kc-field{display:grid;grid-template-columns:92px 1fr;gap:10px;align-items:center;margin:8px 0}
      .kc-field span{font-size:11px;color:var(--fg2)}
      .kc-field input,.kc-field select{width:100%;height:34px;border:1px solid var(--line);border-radius:8px;
        padding:0 10px;font-size:12px;color:var(--fg);background:#fff;outline:none}
      .kc-field input:focus,.kc-field select:focus{border-color:var(--acc);box-shadow:0 0 0 3px var(--acc-soft)}
      .kc-status{min-height:18px;font-size:11px;color:var(--dim);margin-top:10px}
      .kc-status.err{color:var(--bad)}
      .kc-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:8px}
      @media(max-width:560px){.kc-field{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);

    const wrap = document.createElement("div");
    wrap.innerHTML = `
      <div class="kc-backdrop" id="kc-backdrop" hidden>
        <div class="kc-card" role="dialog" aria-modal="true" aria-label="Key 配置">
          <div class="kc-head">
            <div>
              <div class="kc-title">Key 配置</div>
              <div class="kc-sub">留空不修改；只写本地 keys.json（0600），原始 Key 不进 HTML。</div>
            </div>
            <button class="kc-x" id="kc-close" type="button" aria-label="关闭">×</button>
          </div>

          <div class="kc-section">
            <div class="kc-section-title">RunningHub <span id="kc-rh-mask" class="kc-mask"></span></div>
            <label class="kc-field"><span>API Key</span><input id="kc-rh-key" type="password" autocomplete="off" placeholder="输入新 Key；留空不修改"></label>
          </div>

          <div class="kc-section">
            <div class="kc-section-title">Router <span id="kc-rt-mask" class="kc-mask"></span></div>
            <label class="kc-field"><span>API Key</span><input id="kc-rt-key" type="password" autocomplete="off" placeholder="输入新 Key；留空不修改"></label>
          </div>

          <div class="kc-status" id="kc-status"></div>
          <div class="kc-actions">
            <button class="btn" id="kc-cancel" type="button">取消</button>
            <button class="btn primary" id="kc-save" type="button">保存</button>
          </div>
        </div>
      </div>`;
    modal = wrap.firstElementChild;
    document.body.appendChild(modal);

    $("kc-close").onclick = closeModal;
    $("kc-cancel").onclick = closeModal;
    modal.addEventListener("click", (event) => {
      if (event.target === modal) closeModal();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && modal && !modal.hidden) closeModal();
    });
    $("kc-save").onclick = saveKeys;
  }

  function fillForm(data) {
    const rh = data.runninghub || {};
    const rt = data.router || {};
    $("kc-rh-mask").textContent = rh.configured ? "已配置 " + rh.masked : "未配置";
    $("kc-rt-mask").textContent = rt.configured ? "已配置 " + rt.masked : "未配置";
    $("kc-rh-key").value = "";
    $("kc-rt-key").value = "";
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    ["kc-rh-key", "kc-rt-key"].forEach((id) => {
      const el = $(id);
      if (el) el.value = "";
    });
    setStatus("");
  }

  window.openKeyConfig = async function () {
    ensureModal();
    modal.hidden = false;
    setStatus("读取配置…");
    try {
      fillForm(await api("/api/keys"));
      setStatus("");
    } catch (error) {
      setStatus(String(error.message || error), true);
    }
  };

  window.closeKeyConfig = closeModal;

  function collectIssues(data) {
    const keys = (data && data.keys) || {};
    const issues = [];
    const entries = Object.entries(keys);
    for (const [name, item] of entries) {
      if (item.configured && !item.ok) {
        issues.push((item.label || name) + "：" + (item.error || "查询失败"));
      }
    }
    if (!entries.some(([, item]) => item.configured)) {
      issues.push("未配置 Key");
    }
    return issues;
  }

  async function refreshBalance(silent) {
    if (!silent) setStatus("查询余额…");
    try {
      const data = await api("/api/balance");
      if (data.keys && typeof DATA !== "undefined") {
        DATA.keys = data.keys;
        if (typeof renderTop === "function") renderTop();
        const rh = data.keys.runninghub || {};
        const rt = data.keys.router || {};
        if ($("kc-rh-mask")) {
          $("kc-rh-mask").textContent = rh.configured ? "已配置 " + rh.masked : "未配置";
        }
        if ($("kc-rt-mask")) {
          $("kc-rt-mask").textContent = rt.configured ? "已配置 " + rt.masked : "未配置";
        }
      }
      if (!silent) {
        const issues = collectIssues(data);
        if (issues.length) {
          setStatus(issues.join("；"), true);
        } else {
          const when = data.checked_at ? " · " + String(data.checked_at).replace("T", " ").slice(0, 16) : "";
          setStatus("余额已刷新" + when);
        }
      }
      return data;
    } catch (error) {
      if (!silent) setStatus(String(error.message || error), true);
      throw error;
    }
  }

  async function saveKeys() {
    const payload = {
      runninghub: { api_key: $("kc-rh-key").value.trim() },
      router: { api_key: $("kc-rt-key").value.trim() },
    };
    if (!payload.runninghub.api_key && !payload.router.api_key) {
      setStatus("未输入新 Key，未修改");
      return;
    }
    setStatus("保存中…");
    try {
      await api("/api/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then((saved) => {
        if ($("kc-rh-mask")) {
          $("kc-rh-mask").textContent = saved.runninghub.configured
            ? "已配置 " + saved.runninghub.masked
            : "未配置";
        }
        if ($("kc-rt-mask")) {
          $("kc-rt-mask").textContent = saved.router.configured
            ? "已配置 " + saved.router.masked
            : "未配置";
        }
      });
      $("kc-rh-key").value = "";
      $("kc-rt-key").value = "";
      setStatus("已保存");
      try {
        const data = await refreshBalance(true);
        const issues = collectIssues(data);
        if (issues.length) {
          setStatus("已保存；" + issues.join("；"), true);
        } else {
          setStatus("已保存，余额已刷新");
        }
      } catch (error) {
        setStatus("已保存；余额查询失败：" + String(error.message || error), true);
      }
    } catch (error) {
      setStatus(String(error.message || error), true);
    }
  }

  window.MV_KEY_UI = { refresh: refreshBalance, open: window.openKeyConfig };

  if (window.MV_SERVER_MODE) {
    setTimeout(() => {
      refreshBalance(true).catch(() => {});
    }, 400);
  }
})();
