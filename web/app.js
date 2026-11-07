(function () {
  const DATA = window.STUDY_APP_DATA;
  if (!DATA) {
    document.body.innerHTML = "<div style='padding:30px;color:#fff;'>데이터(data.js)를 불러오지 못했습니다. python run_daily_study.py를 먼저 실행해주세요.</div>";
    return;
  }

  const STORAGE_KEY = "AGY_STOCK_STUDY_STATE_V1";
  let stockChartInstance = null;
  let radarChartInstance = null;

  const defaultState = {
    xp: 60,
    streak: 1,
    lastStudyDate: DATA.today_briefing.study_date,
    skills: {
      macro: 42,
      income_statement: 40,
      balance_sheet: 38,
      valuation: 36,
      technical: 40
    },
    unitScores: {},
    answeredQuizzes: {},
    remindQueue: [],
    studiedVideos: [],
    selectedUnitId: 1,
    selectedFilter: "all",
    selectedTicker: "TSLA",
    selectedSubEventId: DATA.today_briefing.subscriber_event
      ? DATA.today_briefing.subscriber_event.event_id
      : (DATA.subscriber_events[0] && DATA.subscriber_events[0].event_id)
  };

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return JSON.parse(JSON.stringify(defaultState));
      const parsed = JSON.parse(raw);
      return Object.assign({}, defaultState, parsed, {
        skills: Object.assign({}, defaultState.skills, parsed.skills || {})
      });
    } catch (e) {
      return JSON.parse(JSON.stringify(defaultState));
    }
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {}
  }

  let state = loadState();

  function showToast(msg) {
    const el = document.getElementById("toast-notification");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 2600);
  }

  function getCurrentLevelInfo(xp) {
    const levels = DATA.level_system || [];
    for (let i = levels.length - 1; i >= 0; i--) {
      if (xp >= levels[i].min_xp) {
        const curr = levels[i];
        const next = levels[i + 1] || null;
        return { curr, next };
      }
    }
    return { curr: levels[0], next: levels[1] };
  }

  function getWeakestAndStrongestSkill() {
    const labels = {
      macro: "매크로·시황 해석(1단원)",
      income_statement: "손익계산서·EPS 성장성(2단원)",
      balance_sheet: "대차대조표·재무체력(3단원)",
      valuation: "밸류에이션 PER·PEG(4단원)",
      technical: "차트 이평선·매물대(5단원)"
    };
    const entries = Object.entries(state.skills);
    entries.sort((a, b) => a[1] - b[1]);
    const weakest = entries[0];
    const strongest = entries[entries.length - 1];
    return {
      weakKey: weakest[0],
      weakLabel: labels[weakest[0]],
      weakScore: weakest[1],
      strongKey: strongest[0],
      strongLabel: labels[strongest[0]],
      strongScore: strongest[1]
    };
  }

  function addXpAndSkill(amount, skillDomain, reasonMsg) {
    const prevLvl = getCurrentLevelInfo(state.xp).curr.level;
    state.xp += amount;
    if (skillDomain && state.skills[skillDomain] !== undefined) {
      state.skills[skillDomain] = Math.min(100, state.skills[skillDomain] + 6);
    }
    const newLvlInfo = getCurrentLevelInfo(state.xp);
    saveState();
    renderHeader();
    if (newLvlInfo.curr.level > prevLvl) {
      showToast(`🎉 레벨 업!! ${newLvlInfo.curr.badge} 단계에 도달했습니다!`);
    } else if (reasonMsg) {
      showToast(`${reasonMsg} (+${amount} XP)`);
    }
  }

  function addToRemindQueue(qObj, sourceTitle) {
    const exists = state.remindQueue.some((item) => item.q_id === qObj.q_id);
    if (!exists) {
      state.remindQueue.unshift({
        q_id: qObj.q_id,
        question: qObj.question,
        options: qObj.options,
        answer: qObj.answer,
        explanation: qObj.explanation,
        remind_tag: qObj.remind_tag || "핵심 개념 복습",
        skill_domain: qObj.skill_domain || "valuation",
        source: sourceTitle,
        added_at: new Date().toISOString().slice(0, 10)
      });
      saveState();
      renderHeader();
    }
  }

  function renderHeader() {
    const { curr, next } = getCurrentLevelInfo(state.xp);
    document.getElementById("streak-count").textContent = state.streak;
    document.getElementById("user-level-badge").textContent = curr.badge;
    document.getElementById("user-level-summary").textContent = curr.summary;
    document.getElementById("user-xp").textContent = state.xp;

    if (next) {
      const span = next.min_xp - curr.min_xp;
      const progress = Math.min(100, Math.max(8, Math.round(((state.xp - curr.min_xp) / span) * 100)));
      document.getElementById("user-xp-next").textContent = `다음 레벨까지 ${next.min_xp - state.xp} XP`;
      document.getElementById("xp-bar-fill").style.width = `${progress}%`;
    } else {
      document.getElementById("user-xp-next").textContent = "최고 마스터 레벨 달성!";
      document.getElementById("xp-bar-fill").style.width = "100%";
    }

    const diag = getWeakestAndStrongestSkill();
    document.getElementById("ai-coach-short").innerHTML =
      `💡 <strong>AI 레벨 진단:</strong> 강점 <code>${diag.strongLabel}</code>(${diag.strongScore}점) | 보완 추천 <code>${diag.weakLabel}</code>(${diag.weakScore}점)`;

    const badge = document.getElementById("remind-count-badge");
    if (state.remindQueue.length > 0) {
      badge.style.display = "inline-block";
      badge.textContent = state.remindQueue.length;
    } else {
      badge.style.display = "none";
    }
  }

  function buildQuizHtml(qObj, sourceLabel, xpReward, skillDomain) {
    const answered = state.answeredQuizzes[qObj.q_id];
    const domain = qObj.skill_domain || skillDomain || "valuation";
    const optsHtml = qObj.options
      .map((opt, idx) => {
        let cls = "quiz-opt-btn";
        if (answered !== undefined) {
          if (idx === qObj.answer) cls += " correct";
          else if (idx === answered && answered !== qObj.answer) cls += " wrong";
        }
        return `<button class="${cls}" data-qid="${qObj.q_id}" data-idx="${idx}" data-ans="${qObj.answer}" data-xp="${xpReward}" data-domain="${domain}" data-src="${sourceLabel}">
          ${idx + 1}. ${opt}
        </button>`;
      })
      .join("");

    const expDisplay = answered !== undefined ? "block" : "none";
    return `
      <div class="quiz-box" id="qbox-${qObj.q_id}">
        <div class="card-header-line">
          <span class="badge-pill badge-indigo">📝 실전 퀴즈 (${sourceLabel})</span>
          <span class="badge-pill badge-cyan">+${xpReward} XP</span>
        </div>
        <div class="quiz-question">Q. ${qObj.question}</div>
        <div class="quiz-options">${optsHtml}</div>
        <div class="quiz-explanation" id="qexp-${qObj.q_id}" style="display:${expDisplay};">
          <strong>🎯 정답: ${qObj.answer + 1}번</strong><br/>
          💡 ${qObj.explanation}
          <div style="margin-top:6px;">
            <span class="badge-pill badge-amber">🔖 리마인드 키워드: ${qObj.remind_tag || "핵심 개념"}</span>
          </div>
        </div>
      </div>
    `;
  }

  function findQuizById(qid) {
    for (const v of DATA.videos_2026) {
      for (const q of v.daily_quiz || []) {
        if (q.q_id === qid) return q;
      }
    }
    for (const u of DATA.curriculum.units) {
      for (const q of u.quiz || []) {
        if (q.q_id === qid) return q;
      }
    }
    for (const ev of DATA.subscriber_events || []) {
      if (ev.quiz && ev.quiz.q_id === qid) return ev.quiz;
    }
    return null;
  }

  function handleQuizOptionClick(btn) {
    const qid = btn.getAttribute("data-qid");
    const chosen = parseInt(btn.getAttribute("data-idx"), 10);
    const ans = parseInt(btn.getAttribute("data-ans"), 10);
    const xp = parseInt(btn.getAttribute("data-xp"), 10) || 25;
    const domain = btn.getAttribute("data-domain");
    const src = btn.getAttribute("data-src");

    const qObj = findQuizById(qid);
    const alreadyAnswered = state.answeredQuizzes[qid] !== undefined;
    state.answeredQuizzes[qid] = chosen;

    const parent = btn.closest(".quiz-options");
    parent.querySelectorAll(".quiz-opt-btn").forEach((b, i) => {
      b.classList.remove("correct", "wrong");
      if (i === ans) b.classList.add("correct");
      else if (i === chosen && chosen !== ans) b.classList.add("wrong");
    });

    const expEl = document.getElementById(`qexp-${qid}`);
    if (expEl) expEl.style.display = "block";

    if (chosen === ans) {
      if (!alreadyAnswered) {
        addXpAndSkill(xp, domain, "✅ 정답입니다! 역량 점수와 경험치가 상승했습니다");
      } else {
        showToast("✅ 정답입니다!");
      }
    } else {
      if (qObj) {
        addToRemindQueue(qObj, src);
      }
      showToast("❌ 아쉽네요! 오답 리마인드 노트에 자동 등록되어 복습할 수 있습니다.");
    }
    saveState();
  }

  // 탭 1: 오늘의 공부 렌더링
  function renderDailyTab() {
    const remindBox = document.getElementById("remind-alert-box");
    if (state.remindQueue.length > 0) {
      remindBox.innerHTML = `
        <div class="card" style="border-color: rgba(244,63,94,0.5); background: linear-gradient(90deg, rgba(244,63,94,0.15), rgba(19,27,46,0.95));">
          <div class="card-header-line">
            <span class="badge-pill badge-rose">🔔 복습 리마인드 알림</span>
            <button class="btn-mini-diag" id="btn-jump-remind">지금 복습하기 (${state.remindQueue.length}문항) ›</button>
          </div>
          <p style="font-size:0.84rem; color:#fecdd3;">이전에 틀렸거나 헷갈렸던 개념 <strong>${state.remindQueue.length}개</strong>가 리마인드 대기 중입니다. 짧은 테스트로 내 것으로 만드세요!</p>
        </div>
      `;
      const jumpBtn = document.getElementById("btn-jump-remind");
      if (jumpBtn) {
        jumpBtn.onclick = () => switchTab("tab-remind");
      }
    } else {
      remindBox.innerHTML = "";
    }

    const tb = DATA.today_briefing;
    const v = tb.video;
    const mySt = tb.my_stock_spotlight;
    const isVideoDone = state.studiedVideos.includes(v.video_id);

    // 구독자 요청 종목 이벤트 선택 지원
    const subEvents = DATA.subscriber_events || [];
    const activeSub =
      subEvents.find((e) => e.event_id === state.selectedSubEventId) ||
      tb.subscriber_event ||
      subEvents[0];

    const subPillsHtml = subEvents
      .map(
        (ev) => `
        <button class="chip-btn ${ev.event_id === activeSub.event_id ? "active" : ""}" data-subevt="${ev.event_id}">
          🎁 ${ev.ticker} (${ev.name.split(" ")[0]})
        </button>
      `
      )
      .join("");

    const dailyQuizzesHtml = (v.daily_quiz || [])
      .map((q) => buildQuizHtml(q, `오늘의 영상: ${v.published_at}`, 30, q.skill_domain))
      .join("");

    const container = document.getElementById("daily-study-container");
    container.innerHTML = `
      <div class="mode-banner" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <span>${tb.mode_badge}</span>
        <div style="display:flex; gap:6px;">
          <button class="btn-mini-diag" id="btn-next-video-lesson" title="다른 미학습 영상으로 오늘의 공부 변경">⏭️ 다음 영상 공부하기</button>
          <button class="btn-mini-diag" id="btn-reset-quiz-state" title="이미 푼 체크 표시를 지우고 다시 풀기">🔄 퀴즈 기록 초기화</button>
        </div>
      </div>

      <!-- 1. 오늘의 올랜도 킴 메인 영상 5단계 벤치마킹 카드 -->
      <div class="card">
        <div class="card-header-line">
          <span class="badge-pill badge-indigo">🎬 오늘의 기준 영상 (${v.published_at})</span>
          <span class="badge-pill badge-emerald">연결: ${tb.unit_summary.title}</span>
        </div>
        <h2 style="font-size:1.12rem; margin-bottom:6px;">${v.title}</h2>
        <div style="margin-bottom:10px; font-size:0.8rem;">
          <a href="${v.youtube_url}" target="_blank" style="color:#38bdf8; text-decoration:none; margin-right:12px;">▶ 유튜브 원본 영상 열기 ↗</a>
          <span style="color:var(--text-muted);">언급 종목: ${v.mentioned_tickers.join(", ")}</span>
        </div>

        <div class="funnel-list">
          <div class="funnel-step"><strong>STEP 1. 매크로 & 시장 심리</strong>${v.orlando_five_step.macro}</div>
          <div class="funnel-step"><strong>STEP 2. 스마트 머니 & 수급</strong>${v.orlando_five_step.smart_money}</div>
          <div class="funnel-step"><strong>STEP 3. 기본적 분석 (손익·대차대조표)</strong>${v.orlando_five_step.fundamental}</div>
          <div class="funnel-step"><strong>STEP 4. 기술적 분석 (차트·이평선·매물대)</strong>${v.orlando_five_step.technical}</div>
          <div class="funnel-step"><strong>STEP 5. 조건부 시나리오 대응 원칙</strong>${v.orlando_five_step.action_plan}</div>
        </div>

        <!-- 기본적 분석 50% × 기술적 분석 50% 균형 학습 박스 -->
        <div class="dual-grid">
          <div class="balance-box fund">
            <span class="badge-pill badge-cyan" style="margin-bottom:6px;">기본적 분석 50% (재무·대차대조표)</span>
            <h4>📊 ${v.fundamental_lesson.concept}</h4>
            <p>${v.fundamental_lesson.detail}</p>
          </div>
          <div class="balance-box tech">
            <span class="badge-pill badge-emerald" style="margin-bottom:6px;">기술적 분석 50% (차트·이평선)</span>
            <h4>📈 ${v.technical_lesson.concept}</h4>
            <p>${v.technical_lesson.detail}</p>
          </div>
        </div>

        <div style="background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.3); padding:11px 13px; border-radius:10px; font-size:0.84rem; margin-top:10px;">
          <strong>🔗 내 포트폴리오 연결 인사이트:</strong> ${v.my_portfolio_connection}
        </div>

        <div style="margin-top:12px; display:flex; justify-content:space-between; align-items:center;">
          <button class="primary-btn" id="btn-complete-video" data-vid="${v.video_id}" ${isVideoDone ? "disabled style='opacity:0.6;'" : ""}>
            ${isVideoDone ? "✅ 오늘 영상 학습 완료됨" : "✅ 오늘 영상 개념 학습 완료 체크 (+40 XP)"}
          </button>
          <button class="btn-mini-diag" id="btn-go-matched-unit" data-unit="${tb.unit_summary.unit_id}">
            연결 단원(${tb.unit_summary.unit_id}단원) 자세히 보기 ›
          </button>
        </div>

        ${dailyQuizzesHtml}
      </div>

      <!-- 2. 구독자 요청 종목 스페셜 이벤트 학습 코너 -->
      <div class="card sub-event-card">
        <div class="card-header-line">
          <span class="badge-pill badge-amber">🎁 구독자 요청 종목 이벤트 스터디</span>
          <span class="badge-pill badge-emerald">보너스 +${activeSub.bonus_xp} XP</span>
        </div>
        <h3 style="font-size:1.03rem; margin-bottom:4px;">영상 속 구독자 질문 종목을 내가 직접 진단해보기</h3>
        <p style="font-size:0.82rem; color:var(--text-secondary); margin-bottom:10px;">
          올랜도 킴 영상에서 구독자들이 요청한 핫 종목들입니다. 종목 버튼을 눌러 각각의 대차대조표 특징과 차트 타점을 이벤트 퀴즈로 정복하세요!
        </p>
        <div class="ticker-chips">${subPillsHtml}</div>

        <div class="quote-bubble">💬 <strong>${activeSub.name} (${activeSub.ticker})</strong> — ${activeSub.subscriber_story}</div>
        <div style="font-size:0.86rem; font-weight:700; color:#6ee7b7; margin:8px 0;">
          ⚡ 올랜도 킴 식 한 줄 처방: ${activeSub.orlando_verdict}
        </div>
        <div class="dual-grid">
          <div class="balance-box fund">
            <h4>📊 대차대조표 & 손익 팩트체크</h4>
            <p>${activeSub.fundamental_check}</p>
          </div>
          <div class="balance-box tech">
            <h4>📈 차트 이평선 & 매물대 체크</h4>
            <p>${activeSub.technical_check}</p>
          </div>
        </div>
        <div style="margin-top:8px;">
          <button class="btn-mini-diag" data-labticker="${activeSub.ticker}" id="btn-open-sub-in-lab">
            📊 종목 랩에서 ${activeSub.ticker} 대차대조표·차트 크게 보기 ›
          </button>
        </div>
        ${buildQuizHtml(activeSub.quiz, `구독자 요청 이벤트: ${activeSub.ticker}`, activeSub.bonus_xp, activeSub.quiz.skill_domain)}
      </div>

      <!-- 3. 오늘의 내 보유종목 실전 대조 스포트라이트 -->
      <div class="card">
        <div class="card-header-line">
          <span class="badge-pill badge-cyan">💼 오늘의 내 보유종목 실전 점검</span>
          <span class="badge-pill badge-indigo">${mySt.ticker} • 평단 $${mySt.my_avg_usd}</span>
        </div>
        <h3 style="font-size:1.02rem; margin-bottom:6px;">${mySt.name} — 재무(대차대조표) × 차트 균형 점검</h3>
        <div class="kpi-grid">
          <div class="kpi-item">
            <div class="kpi-label">대차대조표 등급</div>
            <div class="kpi-val" style="color:#38bdf8; font-size:0.82rem;">${mySt.fundamental.bs_grade}</div>
          </div>
          <div class="kpi-item">
            <div class="kpi-label">현재가 / 20일선</div>
            <div class="kpi-val">$${mySt.technical.current_price} / $${mySt.technical.ma20}</div>
          </div>
          <div class="kpi-item">
            <div class="kpi-label">지지선 / 저항선</div>
            <div class="kpi-val">$${mySt.technical.support} / $${mySt.technical.resistance}</div>
          </div>
        </div>
        <p style="font-size:0.83rem; color:var(--text-secondary); margin-bottom:6px;">
          <strong>• 대차대조표 포인트:</strong> ${mySt.fundamental.bs_comment}
        </p>
        <p style="font-size:0.83rem; color:var(--text-secondary); margin-bottom:8px;">
          <strong>• 차트 대응 포인트:</strong> ${mySt.technical.tech_comment}
        </p>
        <button class="btn-mini-diag" id="btn-open-my-in-lab" data-labticker="${mySt.ticker}">
          내 보유종목 전체 대차대조표·차트 비교하러 가기 ›
        </button>
      </div>
    `;

    // 이벤트 바인딩
    const btnCompleteVideo = document.getElementById("btn-complete-video");
    if (btnCompleteVideo) {
      btnCompleteVideo.onclick = () => {
        const vid = btnCompleteVideo.getAttribute("data-vid");
        if (!state.studiedVideos.includes(vid)) {
          state.studiedVideos.push(vid);
          addXpAndSkill(40, "macro", "🎬 오늘의 영상 5단계 프레임워크 학습 완료!");
          renderDailyTab();
        }
      };
    }

    const btnNextVideo = document.getElementById("btn-next-video-lesson");
    if (btnNextVideo) {
      btnNextVideo.onclick = () => {
        const allVids = DATA.videos_2026 || [];
        const currIdx = allVids.findIndex((x) => x.video_id === v.video_id);
        const nextVid = allVids[(currIdx + 1) % allVids.length];
        if (nextVid) {
          DATA.today_briefing.video = nextVid;
          DATA.today_briefing.mode_badge = `🟢 [연속 학습 모드] ${nextVid.published_at} 영상 (${(currIdx + 2)}/${allVids.length}번째)`;
          const matchedU =
            DATA.curriculum.units.find((u) => u.unit_id === nextVid.related_unit) ||
            DATA.curriculum.units[0];
          DATA.today_briefing.unit_summary = {
            unit_id: matchedU.unit_id,
            title: matchedU.title,
            subtitle: matchedU.subtitle
          };
          showToast(`⏭️ 다음 영상 『${nextVid.title}』 및 새 퀴즈를 불러왔습니다!`);
          renderDailyTab();
        }
      };
    }

    const btnResetQuiz = document.getElementById("btn-reset-quiz-state");
    if (btnResetQuiz) {
      btnResetQuiz.onclick = () => {
        state.answeredQuizzes = {};
        saveState();
        showToast("🔄 모든 퀴즈의 정답 체크 표시가 초기화되었습니다! 처음부터 다시 풀어보세요.");
        renderDailyTab();
      };
    }

    const btnGoUnit = document.getElementById("btn-go-matched-unit");
    if (btnGoUnit) {
      btnGoUnit.onclick = () => {
        state.selectedUnitId = parseInt(btnGoUnit.getAttribute("data-unit"), 10) || 1;
        saveState();
        switchTab("tab-curriculum");
      };
    }

    container.querySelectorAll("[data-subevt]").forEach((btn) => {
      btn.onclick = () => {
        state.selectedSubEventId = btn.getAttribute("data-subevt");
        saveState();
        renderDailyTab();
      };
    });

    container.querySelectorAll("[data-labticker]").forEach((btn) => {
      btn.onclick = () => {
        state.selectedTicker = btn.getAttribute("data-labticker");
        state.selectedFilter = "all";
        saveState();
        switchTab("tab-lab");
      };
    });
  }

  // 탭 2: 6단원 커리큘럼 및 단원별 테스트 렌더링
  function renderCurriculumTab() {
    const units = DATA.curriculum.units || [];
    const pillsEl = document.getElementById("unit-pills");
    pillsEl.innerHTML = units
      .map((u) => {
        const scoreInfo = state.unitScores[u.unit_id];
        const mark = scoreInfo && scoreInfo.passed ? "🏅" : "📖";
        const activeCls = u.unit_id === state.selectedUnitId ? "active" : "";
        return `<button class="chip-btn ${activeCls}" data-unitid="${u.unit_id}">${mark} ${u.unit_id}단원</button>`;
      })
      .join("");

    pillsEl.querySelectorAll("[data-unitid]").forEach((btn) => {
      btn.onclick = () => {
        state.selectedUnitId = parseInt(btn.getAttribute("data-unitid"), 10);
        saveState();
        renderCurriculumTab();
      };
    });

    const unit = units.find((u) => u.unit_id === state.selectedUnitId) || units[0];
    const scoreObj = state.unitScores[unit.unit_id];
    const statusBadge =
      scoreObj && scoreObj.passed
        ? `<span class="badge-pill badge-emerald">🏅 마스터 완료 (${scoreObj.score}/${unit.quiz.length}점)</span>`
        : `<span class="badge-pill badge-amber">🎯 목표: 5문항 중 4문항(80%) 이상 통과 시 마스터</span>`;

    const fundConceptsHtml = unit.fundamental_section.core_concepts
      .map(
        (c) => `
        <div style="margin-bottom:12px;">
          <strong style="color:#67e8f9; font-size:0.88rem;">• ${c.term}</strong>
          <span class="formula-chip">${c.formula}</span>
          <p style="font-size:0.83rem; color:var(--text-secondary);">${c.explanation}</p>
        </div>
      `
      )
      .join("");

    const techConceptsHtml = unit.technical_section.core_concepts
      .map(
        (c) => `
        <div style="margin-bottom:12px;">
          <strong style="color:#6ee7b7; font-size:0.88rem;">• ${c.term}</strong>
          <span class="formula-chip" style="color:#6ee7b7; border-color:rgba(16,185,129,0.3); background:rgba(16,185,129,0.1);">${c.pattern}</span>
          <p style="font-size:0.83rem; color:var(--text-secondary);">${c.explanation}</p>
        </div>
      `
      )
      .join("");

    const unitDomainMap = {
      1: "macro",
      2: "income_statement",
      3: "balance_sheet",
      4: "valuation",
      5: "technical",
      6: "valuation"
    };
    const domain = unitDomainMap[unit.unit_id] || "valuation";

    const unitQuizHtml = unit.quiz
      .map((q) => buildQuizHtml(q, `${unit.unit_id}단원 테스트`, 25, domain))
      .join("");

    const detailEl = document.getElementById("unit-detail-container");
    detailEl.innerHTML = `
      <div class="card">
        <div class="card-header-line">
          <span class="badge-pill badge-indigo">Unit ${unit.unit_id} • 권장 ${unit.estimated_minutes}분</span>
          ${statusBadge}
        </div>
        <h2 style="font-size:1.15rem; margin-bottom:4px;">${unit.title}</h2>
        <p style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:12px;">${unit.subtitle}</p>

        <div style="background:rgba(15,23,42,0.7); padding:12px; border-radius:10px; margin-bottom:14px;">
          <strong style="font-size:0.84rem; color:#a5b4fc;">🎯 이 단원을 마치면 할 수 있어요:</strong>
          <ul style="padding-left:18px; margin-top:6px; font-size:0.83rem; color:var(--text-secondary);">
            ${unit.learning_objectives.map((o) => `<li>${o}</li>`).join("")}
          </ul>
        </div>

        <div class="dual-grid">
          <div class="balance-box fund">
            <h4>${unit.fundamental_section.title}</h4>
            ${fundConceptsHtml}
          </div>
          <div class="balance-box tech">
            <h4>${unit.technical_section.title}</h4>
            ${techConceptsHtml}
          </div>
        </div>

        <div style="background:linear-gradient(135deg, rgba(99,102,241,0.16), rgba(15,23,42,0.9)); border:1px solid rgba(99,102,241,0.35); padding:13px; border-radius:12px; margin-top:12px;">
          <span class="badge-pill badge-indigo" style="margin-bottom:6px;">🎬 올랜도 킴 2026 실제 영상 벤치마킹 케이스</span>
          <h4 style="font-size:0.92rem; margin-bottom:4px;">『${unit.orlando_case_study.video_title}』 (${unit.orlando_case_study.video_date})</h4>
          <p style="font-size:0.83rem; color:var(--text-secondary); margin-bottom:6px;">${unit.orlando_case_study.how_orlando_analyzed}</p>
          <p style="font-size:0.83rem; color:#67e8f9; font-weight:600;">👉 실천 과제: ${unit.orlando_case_study.actionable_takeaway}</p>
        </div>
      </div>

      <div class="card">
        <div class="card-header-line">
          <h3 style="font-size:1.05rem;">✍️ ${unit.unit_id}단원 마무리 테스트 & 리마인드 점검 (총 ${unit.quiz.length}문항)</h3>
          <button class="primary-btn" id="btn-grade-unit" data-unitid="${unit.unit_id}">📊 단원 성적표 합산 & 마스터 인증</button>
        </div>
        <p style="font-size:0.82rem; color:var(--text-secondary); margin-bottom:10px;">
          각 문항을 클릭해 풀고 해설을 확인한 뒤 <strong>[단원 성적표 합산 & 마스터 인증]</strong> 버튼을 누르세요. 틀린 문제는 자동으로 오답 리마인드 노트에 등록됩니다.
        </p>
        <div id="unit-grade-banner"></div>
        ${unitQuizHtml}
      </div>
    `;

    const btnGrade = document.getElementById("btn-grade-unit");
    if (btnGrade) {
      btnGrade.onclick = () => {
        let correctCount = 0;
        let answeredCount = 0;
        unit.quiz.forEach((q) => {
          const ans = state.answeredQuizzes[q.q_id];
          if (ans !== undefined) {
            answeredCount++;
            if (ans === q.answer) correctCount++;
            else addToRemindQueue(q, `${unit.unit_id}단원 테스트`);
          }
        });

        const total = unit.quiz.length;
        const passed = correctCount >= Math.ceil(total * 0.8);
        const alreadyPassed = state.unitScores[unit.unit_id] && state.unitScores[unit.unit_id].passed;

        state.unitScores[unit.unit_id] = {
          score: correctCount,
          total: total,
          passed: passed,
          updated_at: new Date().toISOString().slice(0, 10)
        };

        if (passed && !alreadyPassed) {
          addXpAndSkill(120, domain, `🏅 축하합니다! ${unit.unit_id}단원 마스터 테스트 통과!`);
        } else {
          saveState();
          renderHeader();
        }

        const bannerEl = document.getElementById("unit-grade-banner");
        bannerEl.innerHTML = `
          <div style="padding:12px; border-radius:10px; margin:10px 0; background:${
            passed ? "rgba(16,185,129,0.2)" : "rgba(244,63,94,0.2)"
          }; border:1px solid ${passed ? "#10b981" : "#f43f5e"};">
            <strong>${
              passed
                ? `🏅 단원 마스터 성공! (${correctCount} / ${total} 정답)`
                : `⚠️ 재도전 필요 (${correctCount} / ${total} 정답 — 통과 기준 4점 이상)`
            }</strong>
            <p style="font-size:0.82rem; margin-top:4px;">
              ${
                passed
                  ? "기본적 분석과 기술적 분석의 핵심 원리를 훌륭하게 이해하셨습니다! 다음 단원으로 이동하거나 종목 랩에서 실습해보세요."
                  : "틀린 문제는 [진단·리마인드] 탭의 오답 노트에 저장되었습니다. 해설을 읽고 다시 선택해 풀어보세요!"
              }
            </p>
          </div>
        `;
      };
    }
  }

  // 탭 3: 실전 기업 분석 랩 (대차대조표 시각화 + 차트 캔버스 + 구독자 요청 종목)
  function renderLabTab() {
    const allStocks = DATA.market_snapshots.stocks || [];
    const filterBar = document.getElementById("stock-group-filter");
    filterBar.querySelectorAll(".filter-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-filter") === state.selectedFilter);
      btn.onclick = () => {
        state.selectedFilter = btn.getAttribute("data-filter");
        saveState();
        renderLabTab();
      };
    });

    const filtered = allStocks.filter((s) => {
      if (state.selectedFilter === "my") return s.is_my_holding;
      if (state.selectedFilter === "sub") return s.is_subscriber_request;
      if (state.selectedFilter === "orlando") return !s.is_my_holding && !s.is_subscriber_request;
      return true;
    });

    if (!filtered.some((s) => s.ticker === state.selectedTicker) && filtered.length > 0) {
      state.selectedTicker = filtered[0].ticker;
    }

    const chipsEl = document.getElementById("ticker-chips");
    chipsEl.innerHTML = filtered
      .map((s) => {
        const icon = s.is_subscriber_request ? "🎁 " : s.is_my_holding ? "💼 " : "🎯 ";
        const act = s.ticker === state.selectedTicker ? "active" : "";
        return `<button class="chip-btn ${act}" data-ticker="${s.ticker}">${icon}${s.ticker} (${s.name.split(" ")[0]})</button>`;
      })
      .join("");

    chipsEl.querySelectorAll("[data-ticker]").forEach((btn) => {
      btn.onclick = () => {
        state.selectedTicker = btn.getAttribute("data-ticker");
        saveState();
        renderLabTab();
      };
    });

    const st = allStocks.find((s) => s.ticker === state.selectedTicker) || allStocks[0];
    const f = st.fundamental;
    const t = st.technical;

    // 대차대조표 막대 길이 비율 계산
    const maxBs = Math.max(f.cash_billion || 1, f.debt_billion || 1, f.equity_billion || 1, 1);
    const cashPct = Math.min(100, Math.max(6, Math.round((f.cash_billion / maxBs) * 100)));
    const debtPct = Math.min(100, Math.max(6, Math.round((f.debt_billion / maxBs) * 100)));
    const eqPct = Math.min(100, Math.max(6, Math.round((f.equity_billion / maxBs) * 100)));

    let myReturnHtml = "";
    if (st.is_my_holding && st.my_avg_usd) {
      const retPct = (((t.current_price - st.my_avg_usd) / st.my_avg_usd) * 100).toFixed(2);
      const isUp = parseFloat(retPct) >= 0;
      myReturnHtml = `
        <div style="background:rgba(6,182,212,0.12); border:1px solid rgba(6,182,212,0.35); padding:10px 12px; border-radius:10px; margin-bottom:12px; font-size:0.84rem;">
          💼 <strong>내 보유 현황 (${st.my_shares}주):</strong> 평단가 <code>$${st.my_avg_usd}</code> vs 현재가 <code>$${t.current_price}</code>
          (<strong style="color:${isUp ? "#34d399" : "#fb7185"};">${isUp ? "+" : ""}${retPct}%</strong>)
        </div>
      `;
    }

    let subQuestionHtml = "";
    if (st.is_subscriber_request && st.subscriber_question) {
      subQuestionHtml = `
        <div class="quote-bubble">
          🎁 <strong>구독자 분석 요청 질문:</strong> "${st.subscriber_question}"
        </div>
      `;
    }

    const detailEl = document.getElementById("stock-lab-detail");
    detailEl.innerHTML = `
      <div class="card">
        <div class="card-header-line">
          <span class="badge-pill badge-indigo">${st.group}</span>
          <span class="badge-pill badge-emerald">대차대조표 등급: ${f.bs_grade}</span>
        </div>
        <h2 style="font-size:1.15rem; margin-bottom:8px;">${st.name} (${st.ticker})</h2>
        ${myReturnHtml}
        ${subQuestionHtml}

        <div class="dual-grid">
          <!-- 좌: 기본적 분석 (대차대조표 & 손익/밸류) -->
          <div class="balance-box fund">
            <h4>📊 1. 기본적 분석 (대차대조표 & 손익·밸류)</h4>
            <div class="bs-visual-wrap">
              <div style="font-size:0.76rem; color:var(--text-muted); margin-bottom:6px;">대차대조표 스케일 비교 (단위: $B, 십억 달러)</div>
              <div class="bs-bar-row">
                <span class="bs-bar-label">현금성자산</span>
                <div class="bs-bar-track"><div style="width:${cashPct}%; height:100%; background:#38bdf8;"></div></div>
                <span class="bs-bar-val" style="color:#38bdf8;">$${f.cash_billion}B</span>
              </div>
              <div class="bs-bar-row">
                <span class="bs-bar-label">총부채(빚)</span>
                <div class="bs-bar-track"><div style="width:${debtPct}%; height:100%; background:#f43f5e;"></div></div>
                <span class="bs-bar-val" style="color:#fda4af;">$${f.debt_billion}B</span>
              </div>
              <div class="bs-bar-row">
                <span class="bs-bar-label">주주자본</span>
                <div class="bs-bar-track"><div style="width:${eqPct}%; height:100%; background:#10b981;"></div></div>
                <span class="bs-bar-val" style="color:#6ee7b7;">$${f.equity_billion}B</span>
              </div>
            </div>

            <div class="kpi-grid">
              <div class="kpi-item"><div class="kpi-label">유동비율</div><div class="kpi-val">${f.current_ratio}</div></div>
              <div class="kpi-item"><div class="kpi-label">부채비율</div><div class="kpi-val">${f.debt_to_equity}</div></div>
              <div class="kpi-item"><div class="kpi-label">매출성장(YoY)</div><div class="kpi-val">${f.rev_growth_yoy}</div></div>
              <div class="kpi-item"><div class="kpi-label">영업이익률</div><div class="kpi-val">${f.op_margin}</div></div>
              <div class="kpi-item"><div class="kpi-label">선행 PER</div><div class="kpi-val">${f.forward_per}</div></div>
              <div class="kpi-item"><div class="kpi-label">PEG 배수</div><div class="kpi-val">${f.peg}</div></div>
            </div>

            <p style="font-size:0.82rem; margin-top:8px;"><strong>• 대차대조표 진단:</strong> ${f.bs_comment}</p>
            <p style="font-size:0.82rem; margin-top:6px;"><strong>• 손익·밸류 진단:</strong> ${f.val_comment}</p>
          </div>

          <!-- 우: 기술적 분석 (차트 & 이평선 & 지지/저항) -->
          <div class="balance-box tech">
            <h4>📈 2. 기술적 분석 (이평선 배열 & 매물대 지지·저항)</h4>
            <div class="chart-box">
              <canvas id="labStockChart"></canvas>
            </div>
            <div class="kpi-grid">
              <div class="kpi-item"><div class="kpi-label">현재가 / 5일선</div><div class="kpi-val">$${t.current_price} / $${t.ma5}</div></div>
              <div class="kpi-item"><div class="kpi-label">20일 / 60일선</div><div class="kpi-val">$${t.ma20} / $${t.ma60}</div></div>
              <div class="kpi-item"><div class="kpi-label">14일 RSI</div><div class="kpi-val">${t.rsi}</div></div>
            </div>
            <p style="font-size:0.82rem; margin-top:6px;"><strong>• 이평선 배열:</strong> <span style="color:#6ee7b7;">${t.ma_alignment}</span></p>
            <p style="font-size:0.82rem; margin-top:4px;"><strong>• 수급/매물대:</strong> ${t.volume_signal}</p>
            <p style="font-size:0.82rem; margin-top:6px;"><strong>• 차트 실전 가이드:</strong> ${t.tech_comment}</p>
          </div>
        </div>

        <div style="background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.35); padding:11px 13px; border-radius:10px; font-size:0.84rem; margin-top:10px;">
          🎯 <strong>${st.ticker} 핵심 학습 포인트:</strong> ${st.study_point}
        </div>
      </div>
    `;

    drawLabChart(st);
  }

  function drawLabChart(st) {
    const ctx = document.getElementById("labStockChart");
    if (!ctx || typeof Chart === "undefined") return;
    if (stockChartInstance) {
      stockChartInstance.destroy();
    }
    const prices = st.technical.price_history || [];
    const labels = prices.map((_, idx) => `D-${prices.length - 1 - idx}`);
    labels[labels.length - 1] = "현재";

    const ma20Line = prices.map(() => st.technical.ma20);
    const supLine = prices.map(() => st.technical.support);
    const resLine = prices.map(() => st.technical.resistance);

    stockChartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: `${st.ticker} 종가`,
            data: prices,
            borderColor: "#38bdf8",
            backgroundColor: "rgba(56, 189, 248, 0.15)",
            borderWidth: 2.5,
            tension: 0.25,
            fill: true,
            pointRadius: 2.5
          },
          {
            label: `20일 생명선 ($${st.technical.ma20})`,
            data: ma20Line,
            borderColor: "#fbbf24",
            borderWidth: 1.6,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false
          },
          {
            label: `직전고점 저항 ($${st.technical.resistance})`,
            data: resLine,
            borderColor: "#f43f5e",
            borderWidth: 1.3,
            borderDash: [2, 3],
            pointRadius: 0,
            fill: false
          },
          {
            label: `핵심 지지선 ($${st.technical.support})`,
            data: supLine,
            borderColor: "#10b981",
            borderWidth: 1.3,
            borderDash: [2, 3],
            pointRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: "#cbd5e1", font: { size: 10 }, boxWidth: 12 }
          }
        },
        scales: {
          x: { ticks: { color: "#94a3b8", font: { size: 10 } }, grid: { display: false } },
          y: { ticks: { color: "#94a3b8", font: { size: 10 } }, grid: { color: "rgba(148,163,184,0.1)" } }
        }
      }
    });
  }

  // 탭 4: 레벨 진단 & 오답 리마인드 복습 노트
  function renderRemindTab() {
    const diag = getWeakestAndStrongestSkill();
    const { curr } = getCurrentLevelInfo(state.xp);

    const levelStepsHtml = (DATA.level_system || [])
      .map((lv) => {
        const isCurrent = lv.level === curr.level;
        const isDone = lv.level < curr.level;
        return `
        <div style="padding:9px 12px; border-radius:10px; margin-bottom:6px; border:1px solid ${
          isCurrent ? "#6366f1" : "var(--border-subtle)"
        }; background:${isCurrent ? "rgba(99,102,241,0.2)" : "rgba(15,23,42,0.6)"}; display:flex; justify-content:space-between; align-items:center; font-size:0.82rem;">
          <div>
            <strong>${lv.badge}</strong> ${isCurrent ? "<span class='badge-pill badge-indigo'>현재 나의 단계</span>" : isDone ? "✅" : ""}
            <div style="color:var(--text-secondary); font-size:0.78rem;">${lv.summary}</div>
          </div>
          <span style="color:#38bdf8; font-weight:700; white-space:nowrap; margin-left:8px;">${lv.min_xp} XP+</span>
        </div>
      `;
      })
      .join("");

    let remindListHtml = "";
    if (state.remindQueue.length === 0) {
      remindListHtml = `
        <div style="text-align:center; padding:24px 12px; color:var(--text-secondary); font-size:0.86rem;">
          🎉 현재 밀린 오답 리마인드 문제가 없습니다!<br/>
          단원별 테스트나 오늘의 퀴즈를 풀다가 틀리는 문제가 생기면 이곳에 자동으로 모여 복습을 도와드립니다.
        </div>
      `;
    } else {
      remindListHtml = state.remindQueue
        .map(
          (item) => `
          <div class="quiz-box" style="margin-bottom:12px;">
            <div class="card-header-line">
              <span class="badge-pill badge-rose">🔖 리마인드: ${item.remind_tag}</span>
              <span style="font-size:0.75rem; color:var(--text-muted);">출처: ${item.source}</span>
            </div>
            <div class="quiz-question">Q. ${item.question}</div>
            <div class="quiz-options">
              ${item.options
                .map(
                  (opt, idx) => `
                <button class="quiz-opt-btn remind-opt-btn" data-rqid="${item.q_id}" data-idx="${idx}" data-ans="${item.answer}" data-domain="${item.skill_domain}">
                  ${idx + 1}. ${opt}
                </button>
              `
                )
                .join("")}
            </div>
            <div class="quiz-explanation" id="rem-exp-${item.q_id}">
              <strong>🎯 정답: ${item.answer + 1}번</strong><br/>
              💡 ${item.explanation}<br/>
              <button class="primary-btn" style="margin-top:8px; padding:6px 12px; font-size:0.78rem;" data-graduate="${item.q_id}">
                ✅ 완벽히 이해했어요! 리마인드 졸업 (+20 XP)
              </button>
            </div>
          </div>
        `
        )
        .join("");
    }

    const container = document.getElementById("diagnosis-and-remind-container");
    container.innerHTML = `
      <div class="card">
        <div class="card-header-line">
          <span class="badge-pill badge-indigo">🧠 AI 투자 역량 진단 리포트</span>
          <span class="badge-pill badge-cyan">총 경험치 ${state.xp} XP</span>
        </div>
        <h2 style="font-size:1.1rem; margin-bottom:6px;">나의 5대 주식 분석 역량 밸런스 (기본적 × 기술적)</h2>
        <div class="chart-box" style="height:250px;">
          <canvas id="skillRadarChart"></canvas>
        </div>
        <div style="background:rgba(15,23,42,0.8); border:1px solid var(--border-subtle); padding:12px; border-radius:10px; font-size:0.83rem; margin-top:8px;">
          <p style="margin-bottom:6px;">🌟 <strong>현재 최고 강점:</strong> <code>${diag.strongLabel}</code> (${diag.strongScore}점)</p>
          <p style="margin-bottom:6px;">🔧 <strong>집중 보완 추천:</strong> <code>${diag.weakLabel}</code> (${diag.weakScore}점)</p>
          <p style="color:#67e8f9;">👉 <strong>AI 코치 처방:</strong> ${curr.next_goal}</p>
        </div>
      </div>

      <div class="card">
        <h3 style="font-size:1.02rem; margin-bottom:10px;">📈 성장 로드맵 (초보자 Lv.1 → 올랜도 킴 마스터 Lv.5)</h3>
        ${levelStepsHtml}
      </div>

      <div class="card">
        <div class="card-header-line">
          <h3 style="font-size:1.05rem;">🔄 오답 리마인드 복습 노트 (${state.remindQueue.length}문항)</h3>
        </div>
        <p style="font-size:0.82rem; color:var(--text-secondary); margin-bottom:10px;">
          단원 테스트나 일일 영상 퀴즈에서 틀렸던 문제입니다. 다시 풀어 맞히고 <strong>[리마인드 졸업]</strong>을 누르면 보너스 경험치와 함께 복습이 완료됩니다!
        </p>
        ${remindListHtml}
      </div>
    `;

    drawSkillRadar();

    container.querySelectorAll(".remind-opt-btn").forEach((btn) => {
      btn.onclick = () => {
        const rqid = btn.getAttribute("data-rqid");
        const idx = parseInt(btn.getAttribute("data-idx"), 10);
        const ans = parseInt(btn.getAttribute("data-ans"), 10);
        const parent = btn.closest(".quiz-options");
        parent.querySelectorAll(".remind-opt-btn").forEach((b, i) => {
          b.classList.remove("correct", "wrong");
          if (i === ans) b.classList.add("correct");
          else if (i === idx && idx !== ans) b.classList.add("wrong");
        });
        const exp = document.getElementById(`rem-exp-${rqid}`);
        if (exp) exp.style.display = "block";
      };
    });

    container.querySelectorAll("[data-graduate]").forEach((btn) => {
      btn.onclick = () => {
        const rqid = btn.getAttribute("data-graduate");
        state.remindQueue = state.remindQueue.filter((item) => item.q_id !== rqid);
        addXpAndSkill(20, diag.weakKey, "🎓 리마인드 복습 완료! 약점 역량이 보완되었습니다");
        renderRemindTab();
      };
    });
  }

  function drawSkillRadar() {
    const ctx = document.getElementById("skillRadarChart");
    if (!ctx || typeof Chart === "undefined") return;
    if (radarChartInstance) radarChartInstance.destroy();

    const s = state.skills;
    radarChartInstance = new Chart(ctx, {
      type: "radar",
      data: {
        labels: [
          "매크로·시황(1단원)",
          "손익·EPS성장(2단원)",
          "대차대조표·재무(3단원)",
          "밸류에이션(4단원)",
          "차트·매물대(5단원)"
        ],
        datasets: [
          {
            label: "나의 현재 역량 점수",
            data: [s.macro, s.income_statement, s.balance_sheet, s.valuation, s.technical],
            backgroundColor: "rgba(99, 102, 241, 0.28)",
            borderColor: "#818cf8",
            pointBackgroundColor: "#38bdf8",
            borderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            min: 0,
            max: 100,
            ticks: { stepSize: 25, display: false },
            grid: { color: "rgba(148, 163, 184, 0.2)" },
            angleLines: { color: "rgba(148, 163, 184, 0.2)" },
            pointLabels: { color: "#e2e8f0", font: { size: 11, weight: "600" } }
          }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
  }

  // 탭 5: 2026 올랜도 킴 영상 아카이브
  function renderArchiveTab() {
    const videos = DATA.videos_2026 || [];
    const container = document.getElementById("archive-list-container");
    container.innerHTML = videos
      .map((v) => {
        const done = state.studiedVideos.includes(v.video_id);
        return `
        <div class="card">
          <div class="card-header-line">
            <span class="badge-pill badge-indigo">${v.published_at} • ${v.category}</span>
            <span class="badge-pill ${done ? "badge-emerald" : "badge-amber"}">${
          done ? "✅ 학습 완료" : "📌 미학습"
        }</span>
          </div>
          <h3 style="font-size:1rem; margin-bottom:6px;">${v.title}</h3>
          <p style="font-size:0.82rem; color:var(--text-secondary); margin-bottom:6px;">
            <strong>• 기본적 분석 핵심:</strong> ${v.fundamental_lesson.concept}<br/>
            <strong>• 기술적 분석 핵심:</strong> ${v.technical_lesson.concept}
          </p>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; gap:8px; flex-wrap:wrap;">
            <a href="${v.youtube_url}" target="_blank" style="color:#38bdf8; font-size:0.8rem; text-decoration:none;">▶ 유튜브 영상 보기 ↗</a>
            <button class="btn-mini-diag" data-loadvideo="${v.video_id}">🔥 이 영상으로 오늘의 공부 진행하기 ›</button>
          </div>
        </div>
      `;
      })
      .join("");

    container.querySelectorAll("[data-loadvideo]").forEach((btn) => {
      btn.onclick = () => {
        const vid = btn.getAttribute("data-loadvideo");
        const found = videos.find((x) => x.video_id === vid);
        if (found) {
          DATA.today_briefing.video = found;
          DATA.today_briefing.mode_badge = `🎯 [선택 영상 집중 학습] ${found.published_at} 아카이브 영상 기반 학습`;
          const matchedUnit =
            DATA.curriculum.units.find((u) => u.unit_id === found.related_unit) ||
            DATA.curriculum.units[0];
          DATA.today_briefing.unit_summary = {
            unit_id: matchedUnit.unit_id,
            title: matchedUnit.title,
            subtitle: matchedUnit.subtitle
          };
          showToast(`🎬 『${found.title}』 영상을 오늘의 공부로 불러왔습니다!`);
          switchTab("tab-daily");
        }
      };
    });
  }

  function switchTab(tabId) {
    document.querySelectorAll(".tab-view").forEach((sec) => {
      sec.classList.toggle("active", sec.id === tabId);
    });
    document.querySelectorAll(".bottom-nav .nav-item").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
    });

    if (tabId === "tab-daily") renderDailyTab();
    else if (tabId === "tab-curriculum") renderCurriculumTab();
    else if (tabId === "tab-lab") renderLabTab();
    else if (tabId === "tab-remind") renderRemindTab();
    else if (tabId === "tab-archive") renderArchiveTab();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // 전역 클릭 위임 (퀴즈 옵션 버튼)
  document.addEventListener("click", (e) => {
    const optBtn = e.target.closest(".quiz-opt-btn:not(.remind-opt-btn)");
    if (optBtn) {
      handleQuizOptionClick(optBtn);
    }
  });

  // 네비게이션 초기화
  document.querySelectorAll(".bottom-nav .nav-item").forEach((btn) => {
    btn.onclick = () => switchTab(btn.getAttribute("data-tab"));
  });

  const btnGoDiag = document.getElementById("btn-go-diagnosis");
  if (btnGoDiag) {
    btnGoDiag.onclick = () => switchTab("tab-remind");
  }

  renderHeader();
  renderDailyTab();
})();

