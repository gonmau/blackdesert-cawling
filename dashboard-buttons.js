(function () {
  const GH_OWNER = 'gonmau';
  const GH_REPO  = 'blackdesert-cawling';
  const GH_WORKFLOWS = {
    crimson: 'crimson_desert_tracker.yml',
    global:  'global_rival_tracker.yml',
    steamdb: 'steamdb_rival_tracker.yml'
  };
  const GH_LABELS = { crimson: '경쟁 트래커', global: '글로벌', steamdb: 'SteamDB' };

  function injectMarkup() {
    const actions = document.getElementById('dashboard-actions');
    if (!actions) return;

    actions.insertAdjacentHTML('beforeend', `
      <span style="width:1px;height:24px;background:#333;margin:0 4px;"></span>
      <button class="gh-dispatch-btn" id="btn-dispatch-crimson" onclick="dispatchWorkflow('crimson')" title="붉은사막 Steam 경쟁 트래커 즉시 실행" style="display:inline-flex;align-items:center;gap:4px;padding:9px 14px;border-radius:5px;font-size:0.85rem;font-weight:700;cursor:pointer;border:1px solid rgba(200,75,49,0.4);background:rgba(200,75,49,0.1);color:#e8735a;">
        <span class="btn-icon">▶</span> 경쟁 트래커
      </button>
      <button class="gh-dispatch-btn" id="btn-dispatch-global" onclick="dispatchWorkflow('global')" title="Global Rival Tracker 즉시 실행" style="display:inline-flex;align-items:center;gap:4px;padding:9px 14px;border-radius:5px;font-size:0.85rem;font-weight:700;cursor:pointer;border:1px solid rgba(34,187,136,0.4);background:rgba(34,187,136,0.1);color:#22bb88;">
        <span class="btn-icon">▶</span> 글로벌
      </button>
      <button class="gh-dispatch-btn" id="btn-dispatch-steamdb" onclick="dispatchWorkflow('steamdb')" title="SteamDB Rival Tracker 즉시 실행" style="display:inline-flex;align-items:center;gap:4px;padding:9px 14px;border-radius:5px;font-size:0.85rem;font-weight:700;cursor:pointer;border:1px solid rgba(232,160,32,0.4);background:rgba(232,160,32,0.1);color:#e8a020;">
        <span class="btn-icon">▶</span> SteamDB
      </button>
      <button onclick="openGhModal()" id="gh-token-status" title="GitHub 설정" style="background:none;border:1px solid #333;color:#888;border-radius:5px;padding:8px 10px;font-size:0.85rem;cursor:pointer;">⚙</button>
    `);

    document.body.insertAdjacentHTML('beforeend', `
      <div id="gh-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:200;align-items:center;justify-content:center;">
        <div style="background:#111520;border:1px solid #333;border-radius:8px;padding:24px;width:90%;max-width:400px;position:relative;">
          <span onclick="closeGhModal()" style="position:absolute;top:12px;right:16px;cursor:pointer;color:#888;font-size:20px;line-height:1;">×</span>
          <div style="font-size:16px;font-weight:700;color:#eee;margin-bottom:6px;">⚙ GitHub Token 설정</div>
          <div style="font-size:13px;color:#888;margin-bottom:14px;line-height:1.6;">
            GitHub <a href="https://github.com/settings/tokens" target="_blank" style="color:#e8a020;">Personal Access Token</a>을 입력하세요.<br>
            <span style="color:#555;">workflow 권한 필요 · 브라우저 로컬에만 저장됨</span>
          </div>
          <div style="font-size:12px;color:#888;margin-bottom:4px;">Personal Access Token</div>
          <input id="gh-token" type="password" placeholder="ghp_xxxxxxxxxxxxxxxxxxxx" style="width:100%;box-sizing:border-box;padding:8px 10px;background:#0a0c10;border:1px solid #333;border-radius:5px;color:#eee;font-size:13px;margin-bottom:12px;">
          <button onclick="saveGhSettings()" style="width:100%;padding:10px;background:#c84b31;color:white;border:none;border-radius:5px;cursor:pointer;font-weight:700;">저장</button>
        </div>
      </div>
    `);

    const style = document.createElement('style');
    style.textContent = `
      @keyframes ghSpin { to { transform: rotate(360deg); } }
      .gh-dispatch-btn:disabled { opacity: 0.4; cursor: not-allowed; }
      .gh-dispatch-btn:hover:not(:disabled) { filter: brightness(1.3); }
    `;
    document.head.appendChild(style);

    document.getElementById('gh-modal').addEventListener('click', e => {
      if (e.target === document.getElementById('gh-modal')) closeGhModal();
    });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeGhModal(); });
  }

  function ghGetToken() { return localStorage.getItem('gh_token') || ''; }
  function ghSetToken(v) { localStorage.setItem('gh_token', v); }

  const _ghPollers = { crimson: null, global: null, steamdb: null };

  window.openGhModal = function () {
    document.getElementById('gh-token').value = ghGetToken();
    document.getElementById('gh-modal').style.display = 'flex';
  };
  window.closeGhModal = function () { document.getElementById('gh-modal').style.display = 'none'; };

  window.saveGhSettings = function () {
    ghSetToken(document.getElementById('gh-token').value.trim());
    closeGhModal();
    showDispatchToast('✅ Token이 저장되었습니다', '#22bb88');
  };

  function setRunBtn(type, state) {
    const btn = document.getElementById('btn-dispatch-' + type);
    const label = GH_LABELS[type];
    const states = {
      idle:      { icon: '▶',  text: label,       disabled: false },
      waiting:   { icon: '⏳', text: '대기 중…',   disabled: true },
      running:   { icon: '↻',  text: '실행 중…',   disabled: true, spin: true },
      success:   { icon: '✓',  text: '완료',       disabled: false },
      failure:   { icon: '✗',  text: '실패',       disabled: false },
      cancelled: { icon: '—',  text: '취소됨',     disabled: false },
    };
    const s = states[state] || states.idle;
    const iconHtml = s.spin
      ? `<span style="display:inline-block;animation:ghSpin 0.7s linear infinite;">${s.icon}</span>`
      : `<span class="btn-icon">${s.icon}</span>`;
    btn.innerHTML = `${iconHtml} ${s.text}`;
    btn.disabled = s.disabled;
    if (state === 'success' || state === 'failure' || state === 'cancelled') {
      clearTimeout(btn._resetTimer);
      btn._resetTimer = setTimeout(() => { clearTimeout(_ghPollers[type]); _ghPollers[type] = null; setRunBtn(type, 'idle'); }, 4000);
    }
  }

  async function pollRunStatus(type, wf, since) {
    const token = ghGetToken();
    const headers = {
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28'
    };
    let attempts = 0;
    const MAX = 60;
    setRunBtn(type, 'waiting');

    const poll = async () => {
      attempts++;
      if (attempts > MAX) { setRunBtn(type, 'idle'); return; }
      try {
        const r = await fetch(
          `https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/actions/workflows/${wf}/runs?per_page=5&created=>=${since}`,
          { headers }
        );
        if (!r.ok) { setRunBtn(type, 'idle'); return; }
        const data = await r.json();
        const run = data.workflow_runs?.[0];
        if (!run) { _ghPollers[type] = setTimeout(poll, 3000); return; }
        const { status, conclusion } = run;
        const runUrl = run.html_url;

        if (status === 'queued' || status === 'waiting') {
          setRunBtn(type, 'waiting');
          _ghPollers[type] = setTimeout(poll, 3000);
        } else if (status === 'in_progress') {
          setRunBtn(type, 'running');
          _ghPollers[type] = setTimeout(poll, 5000);
        } else {
          if (conclusion === 'success') {
            setRunBtn(type, 'success');
            showDispatchToast(`✅ ${GH_LABELS[type]} 완료!`, '#22bb88');
          } else if (conclusion === 'failure') {
            setRunBtn(type, 'failure');
            showDispatchToast(`❌ ${GH_LABELS[type]} 실패 — <a href="${runUrl}" target="_blank" style="color:#e8a020;">로그 보기</a>`, '#e74c3c');
          } else {
            setRunBtn(type, 'cancelled');
          }
        }
      } catch (e) {
        setRunBtn(type, 'idle');
      }
    };
    _ghPollers[type] = setTimeout(poll, 4000);
  }

  window.dispatchWorkflow = async function (type) {
    const token = ghGetToken();
    if (!token) {
      openGhModal();
      showDispatchToast('⚙ 먼저 GitHub Token을 입력해주세요', '#e8a020');
      return;
    }
    if (_ghPollers[type]) return;

    const wf = GH_WORKFLOWS[type];
    const since = new Date(Date.now() - 5000).toISOString().slice(0, 19) + 'Z';
    setRunBtn(type, 'waiting');

    try {
      const res = await fetch(
        `https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/actions/workflows/${wf}/dispatches`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ ref: 'main' })
        }
      );
      if (res.status === 204) {
        showDispatchToast(`🚀 ${GH_LABELS[type]} 실행 요청됨`, '#e8a020');
        pollRunStatus(type, wf, since);
      } else {
        const err = await res.json().catch(() => ({}));
        showDispatchToast(`❌ 실패 (${res.status}): ${err.message || '알 수 없는 오류'}`, '#e74c3c');
        setRunBtn(type, 'idle');
      }
    } catch (e) {
      showDispatchToast(`❌ 네트워크 오류: ${e.message}`, '#e74c3c');
      setRunBtn(type, 'idle');
    }
  };

  function showDispatchToast(msg, color) {
    let t = document.getElementById('gh-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'gh-toast';
      t.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);padding:10px 20px;border-radius:8px;font-size:13px;font-weight:700;z-index:300;transition:opacity 0.4s;white-space:nowrap';
      document.body.appendChild(t);
    }
    t.innerHTML = msg;
    t.style.background = color + '22';
    t.style.border = `1px solid ${color}66`;
    t.style.color = color;
    t.style.opacity = '1';
    clearTimeout(t._hideTimer);
    t._hideTimer = setTimeout(() => { t.style.opacity = '0'; }, 4000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectMarkup);
  } else {
    injectMarkup();
  }
})();
