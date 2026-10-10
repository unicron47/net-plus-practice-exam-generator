/* Network+ Adaptive Practice Exam — vanilla JS, no build step, GitHub Pages friendly.
 *
 * Everything a student does is kept in localStorage under their profile name.
 * Nothing is sent anywhere; there is no server.
 */
'use strict';

/* ──────────────────────────────────────────────────────────────
 * CONFIG — instructor-tunable knobs.  See README for a walkthrough.
 * ────────────────────────────────────────────────────────────── */
const CONFIG = {
  EXAM_SIZE: 40,            // items per exam, PBQs included
  EXAM_MINUTES: 40,         // countdown length

  // Performance-based questions open every exam, as on the real test (5 PBQs of 75 items,
  // 75 minutes). 3 of 40 keeps the same share and the same minute-per-item pace.
  PBQ_PER_EXAM: 3,

  // Weight of a question by how many times it has EVER been missed.
  // Index = miss count; the last entry is used for anything higher.
  MISS_WEIGHT: [1, 8, 20, 35, 50],

  // Each consecutive correct answer multiplies the weight by this, so a
  // question fades out once it is genuinely learned. Floor keeps it possible.
  STREAK_DECAY: 0.4,
  MIN_WEIGHT: 0.05,

  // Hard guarantee: up to this share of the exam is reserved for questions the
  // student has missed and not yet re-learned. Weighted sampling fills the rest.
  MISSED_TARGET_RATIO: 0.6,

  // Correct answers in a row before a previously-missed question counts "mastered"
  // and stops claiming a reserved slot.
  MASTERY_STREAK: 2,
};

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

/* ──────────────────────────────────────────────────────────────
 * State
 * ────────────────────────────────────────────────────────────── */
let BANK = [];            // [{id,row,text,type,options,answer}]
let BY_ID = new Map();
let PBQS = [];            // performance-based questions (data/pbqs.json)
let PBQ_BY_ID = new Map();
let profile = '';
let stats = {};           // qid -> {seen,right,wrong,streak}
let exam = null;          // in-progress or just-finished exam
let ticker = null;

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* ──────────────────────────────────────────────────────────────
 * Storage
 * ────────────────────────────────────────────────────────────── */
const KEY = {
  last: 'npx:lastProfile',
  stats: (p) => `npx:stats:${p}`,
  exam: (p) => `npx:exam:${p}`,
  hist: (p) => `npx:history:${p}`,
};

function load(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
}
function save(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); }
  catch (e) { console.warn('Could not save to localStorage', e); }
}
function statOf(qid) {
  return stats[qid] || (stats[qid] = { seen: 0, right: 0, wrong: 0, streak: 0 });
}
function persistStats() { save(KEY.stats(profile), stats); }
function history() { return load(KEY.hist(profile), []); }

/* ──────────────────────────────────────────────────────────────
 * Adaptive weighting
 *
 *   weight = MISS_WEIGHT[misses] * STREAK_DECAY ^ (correct answers in a row)
 *
 * An unseen question sits at 1.0.  Miss it once and it jumps to 8 — eight times
 * more likely to be drawn than a question you have never seen.  Miss it a second
 * time and it climbs to 20, then 35, then 50.  Every consecutive correct answer
 * cuts the weight to 40% of itself, so a question you have truly learned sinks
 * back below the unseen pool instead of nagging you forever.
 * ────────────────────────────────────────────────────────────── */
function weightOf(qid) {
  const s = stats[qid];
  if (!s || !s.seen) return CONFIG.MISS_WEIGHT[0];
  const tier = Math.min(s.wrong, CONFIG.MISS_WEIGHT.length - 1);
  const w = CONFIG.MISS_WEIGHT[tier] * Math.pow(CONFIG.STREAK_DECAY, s.streak);
  return Math.max(w, CONFIG.MIN_WEIGHT);
}

/** A question the student has missed and not yet re-learned. */
function isWeak(qid) {
  const s = stats[qid];
  return !!s && s.wrong > 0 && s.streak < CONFIG.MASTERY_STREAK;
}

/** Weighted sampling without replacement. */
function drawWeighted(pool, n) {
  const picked = [];
  const items = pool.slice();
  const weights = items.map(weightOf);
  let total = weights.reduce((a, b) => a + b, 0);

  while (picked.length < n && items.length) {
    let r = Math.random() * total;
    let i = 0;
    while (i < items.length - 1 && (r -= weights[i]) > 0) i++;
    picked.push(items[i]);
    total -= weights[i];
    items.splice(i, 1);
    weights.splice(i, 1);
  }
  return picked;
}

/**
 * Build one exam.  Reserved slots go to weak questions first (hard guarantee),
 * the remainder is weighted-random over everything else — so new material keeps
 * appearing, but a student with a big miss list mostly sees their miss list.
 */
function selectQuestions(n) {
  const all = BANK.map((q) => q.id);
  const weak = all.filter(isWeak);
  const reserve = Math.min(weak.length, Math.floor(n * CONFIG.MISSED_TARGET_RATIO));

  const chosen = drawWeighted(weak, reserve);
  const taken = new Set(chosen);
  const rest = all.filter((id) => !taken.has(id));

  return chosen.concat(drawWeighted(rest, n - chosen.length))
               .sort(() => Math.random() - 0.5);
}

/**
 * PBQs for one exam: different types, favouring ones not tried yet or scored low, and
 * avoiding the ones from the previous exam where possible.
 */
function selectPBQs(n) {
  const lastExam = Math.max(0, ...PBQS.map((p) => (stats[p.id] && stats[p.id].lastAt) || 0));
  const weight = (p) => {
    const s = stats[p.id];
    if (!s || !s.seen) return 4;
    return (1 + 4 * (1 - s.last)) * (s.lastAt === lastExam ? 0.2 : 1);
  };
  const picked = [], types = new Set();
  let pool = PBQS.slice();
  while (picked.length < n && pool.length) {
    const fresh = pool.filter((p) => !types.has(p.type));
    const from = fresh.length ? fresh : pool;
    const w = from.map(weight);
    let r = Math.random() * w.reduce((a, b) => a + b, 0), i = 0;
    while (i < from.length - 1 && (r -= w[i]) > 0) i++;
    picked.push(from[i]); types.add(from[i].type);
    pool = pool.filter((p) => p !== from[i]);
  }
  return picked.map((p) => p.id);
}

function shuffled(n) {
  const a = Array.from({ length: n }, (_, i) => i);
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/* ──────────────────────────────────────────────────────────────
 * Exam lifecycle
 * ────────────────────────────────────────────────────────────── */
function newExam(shuffleOptions) {
  const pbqs = selectPBQs(Math.min(CONFIG.PBQ_PER_EXAM, PBQS.length));
  const ids = selectQuestions(CONFIG.EXAM_SIZE - pbqs.length);
  exam = {
    started: Date.now(),
    deadline: Date.now() + CONFIG.EXAM_MINUTES * 60000,
    idx: 0,
    finished: false,
    items: pbqs.map((id) => ({ id, kind: 'pbq', ans: {}, place: {}, flagged: false })).concat(ids.map((id) => ({
      id,
      order: shuffleOptions ? shuffled(BY_ID.get(id).options.length)
                            : BY_ID.get(id).options.map((_, i) => i),
      picked: [],       // original option indices
      flagged: false,
    }))),
  };
  persistExam();
}
function persistExam() { save(KEY.exam(profile), exam); }
function clearExam() { localStorage.removeItem(KEY.exam(profile)); }

const current = () => exam.items[exam.idx];
const qOf = (item) => BY_ID.get(item.id);
const isPbq = (item) => item.kind === 'pbq';
const pbqOf = (item) => PBQ_BY_ID.get(item.id);
const isAnswered = (item) => (isPbq(item)
  ? Object.keys(item.ans || {}).length > 0 || Object.keys(item.place || {}).length > 0
  : item.picked.length > 0);
const itemTitle = (item) => (isPbq(item) ? `PBQ: ${pbqOf(item).title}` : qOf(item).text);
const sameSet = (a, b) => a.length === b.length && a.every((v) => b.includes(v));
const isRight = (item) => sameSet(item.picked, qOf(item).answer);

function gradeAndFinish() {
  stopTimer();
  exam.finished = true;
  exam.ended = Date.now();

  let score = 0, pbqEarned = 0, pbqCount = 0;
  for (const item of exam.items) {
    const s = statOf(item.id);
    s.seen++;
    if (isPbq(item)) {                       // partial credit, like CompTIA's PBQs
      const r = PBQ.grade(pbqOf(item), item);
      item.result = { earned: r.earned, total: r.total, fraction: r.fraction };
      s.last = r.fraction; s.best = Math.max(s.best || 0, r.fraction); s.lastAt = exam.ended;
      score += r.fraction; pbqEarned += r.fraction; pbqCount++;
      continue;
    }
    if (item.picked.length && isRight(item)) { s.right++; s.streak++; score++; }
    else { s.wrong++; s.streak = 0; }
  }
  exam.score = Math.round(score * 10) / 10;
  exam.pbq = pbqCount ? { count: pbqCount, fraction: pbqEarned / pbqCount } : null;

  const h = history();
  h.push({ at: exam.ended, score: exam.score, total: exam.items.length,
           pbq: exam.pbq ? Math.round(exam.pbq.fraction * 100) : undefined,
           seconds: Math.round((exam.ended - exam.started) / 1000) });
  save(KEY.hist(profile), h);
  persistStats();
  clearExam();
  showResults();
}

/* ──────────────────────────────────────────────────────────────
 * Timer
 * ────────────────────────────────────────────────────────────── */
function startTimer() {
  $('timer').hidden = false;
  tick();
  ticker = setInterval(tick, 1000);
}
function stopTimer() {
  clearInterval(ticker);
  ticker = null;
  $('timer').hidden = true;
}
function tick() {
  const left = Math.max(0, exam.deadline - Date.now());
  const m = Math.floor(left / 60000);
  const s = Math.floor((left % 60000) / 1000);
  $('timer-text').textContent = `${m}:${String(s).padStart(2, '0')}`;
  const el = $('timer');
  el.classList.toggle('warn', left <= 300000 && left > 60000);
  el.classList.toggle('crit', left <= 60000);
  if (left === 0) {
    closeModal();
    gradeAndFinish();
  }
}

/* ──────────────────────────────────────────────────────────────
 * Views
 * ────────────────────────────────────────────────────────────── */
function show(view) {
  for (const v of ['home', 'exam', 'results']) $(`view-${v}`).hidden = v !== view;
  window.scrollTo(0, 0);
}

function renderQuestion() {
  const item = current();
  $('q-index').textContent = exam.idx + 1;
  $('q-total').textContent = exam.items.length;
  const card = document.querySelector('.question-card');
  card.classList.toggle('is-pbq', isPbq(item));
  const flagBtn0 = $('btn-flag');
  flagBtn0.setAttribute('aria-pressed', String(item.flagged));
  flagBtn0.querySelector('.flag-label').textContent = item.flagged ? 'Flagged' : 'Flag for review';
  if (isPbq(item)) {
    $('q-type').hidden = true;
    $('q-options').innerHTML = '';
    PBQUI.render($('q-text'), pbqOf(item), item, () => { persistExam(); renderSidebar(); });
    $('btn-prev').disabled = exam.idx === 0;
    $('btn-next').disabled = exam.idx === exam.items.length - 1;
    $('btn-clear').disabled = !isAnswered(item);
    $('btn-clear').textContent = 'Reset PBQ';
    renderSidebar();
    return;
  }
  $('btn-clear').textContent = 'Clear answer';
  const q = qOf(item);
  const [before, exhibit, after] = textParts(q);
  const qText = $('q-text');
  qText.textContent = before;
  if (exhibit !== null) {
    const pre = document.createElement('pre');
    pre.className = 'exhibit';
    pre.textContent = exhibit;
    qText.append(pre, after);
  }
  $('q-type').hidden = q.type !== 'multi';
  if (q.type === 'multi') {
    $('q-type').textContent = `Select ${q.answer.length} answers`;
  }

  const flagBtn = $('btn-flag');
  flagBtn.setAttribute('aria-pressed', String(item.flagged));
  flagBtn.querySelector('.flag-label').textContent = item.flagged ? 'Flagged' : 'Flag for review';

  const form = $('q-options');
  form.innerHTML = '';
  item.order.forEach((orig, pos) => {
    const checked = item.picked.includes(orig);
    const label = document.createElement('label');
    label.className = 'opt' + (checked ? ' sel' : '');
    label.innerHTML =
      `<input type="${q.type === 'multi' ? 'checkbox' : 'radio'}" name="opt" ${checked ? 'checked' : ''}>` +
      `<span class="letter">${LETTERS[pos]}</span><span>${esc(q.options[orig])}</span>`;
    label.querySelector('input').addEventListener('change', () => choose(orig));
    form.appendChild(label);
  });

  $('btn-prev').disabled = exam.idx === 0;
  $('btn-next').disabled = exam.idx === exam.items.length - 1;
  $('btn-clear').disabled = item.picked.length === 0;
  renderSidebar();
}

function choose(orig) {
  const item = current();
  const q = qOf(item);
  if (q.type === 'multi') {
    const i = item.picked.indexOf(orig);
    if (i >= 0) item.picked.splice(i, 1); else item.picked.push(orig);
  } else {
    item.picked = [orig];
  }
  item.picked.sort((a, b) => a - b);
  persistExam();
  renderQuestion();
}

function goTo(i) {
  PBQUI.closePanel();
  exam.idx = Math.max(0, Math.min(exam.items.length - 1, i));
  persistExam();
  renderQuestion();
}

function renderSidebar() {
  const grid = $('grid');
  grid.innerHTML = '';
  exam.items.forEach((item, i) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = i + 1;
    b.className = [isAnswered(item) ? 'answered' : '', item.flagged ? 'flagged' : '',
                   i === exam.idx ? 'current' : '', isPbq(item) ? 'pbq-cell' : ''].filter(Boolean).join(' ');
    b.title = `${isPbq(item) ? 'PBQ' : 'Question'} ${i + 1}${item.flagged ? ' — flagged' : ''}`;
    b.addEventListener('click', () => goTo(i));
    grid.appendChild(b);
  });

  const flagged = exam.items.map((it, i) => ({ it, i })).filter((x) => x.it.flagged);
  $('flag-count').textContent = flagged.length;
  const list = $('flag-list');
  list.innerHTML = '';
  if (!flagged.length) {
    list.innerHTML = '<li class="empty">Nothing flagged yet.</li>';
  } else {
    for (const { it, i } of flagged) {
      const li = document.createElement('li');
      const b = document.createElement('button');
      b.type = 'button';
      b.innerHTML = `<b>Q${i + 1}</b><span>${esc(itemTitle(it).slice(0, 70))}</span>`;
      b.addEventListener('click', () => goTo(i));
      li.appendChild(b);
      list.appendChild(li);
    }
  }
  $('answered-count').textContent = exam.items.filter(isAnswered).length;
  document.querySelector('.progress-line').lastChild.textContent =
    ` of ${exam.items.length} answered`;
}

/* ── results ─────────────────────────────────────────── */
function showResults() {
  const total = exam.items.length;
  const pct = Math.round((exam.score / total) * 100);
  $('score-pct').textContent = pct + '%';
  $('score-raw').textContent = `${exam.score} / ${total}`;
  $('score-pbq').hidden = !exam.pbq;
  if (exam.pbq) $('score-pbq').textContent =
    `PBQs: ${Math.round(exam.pbq.fraction * 100)}% across ${exam.pbq.count} (partial credit counts toward the score)`;
  $('score-ring').style.setProperty('--pct', pct);

  const secs = Math.round((exam.ended - exam.started) / 1000);
  const ranOut = exam.ended >= exam.deadline - 1500;
  $('score-time').textContent =
    `Time used: ${Math.floor(secs / 60)}m ${secs % 60}s${ranOut ? ' — time expired' : ''}`;

  const missed = exam.items.filter((it) => !isPbq(it) && !isRight(it)).length;
  $('score-note').textContent = missed
    ? `The ${missed} question${missed === 1 ? '' : 's'} you missed are now weighted to come back on your next exam.`
    : 'Perfect score — these questions will start fading out of your rotation.';

  renderReview();
  show('results');
}

// A question's text split around its exhibit (a table / command output shown in a mono box).
function textParts(q) {
  if (!q.exhibit) return [q.text, null, ''];
  const lines = q.text.split('\n');
  const cut = q.exhibit_after + 1;
  return [lines.slice(0, cut).join('\n'), q.exhibit, lines.slice(cut).join('\n')];
}

function reviewText(q) {
  const [before, exhibit, after] = textParts(q);
  return esc(before) + (exhibit === null ? '' : `<pre class="exhibit">${esc(exhibit)}</pre>${esc(after)}`);
}

function renderReview() {
  const onlyWrong = $('only-wrong').checked;
  const ol = $('review');
  ol.innerHTML = '';

  exam.items.forEach((item, i) => {
    if (isPbq(item)) {
      const r = item.result || PBQ.grade(pbqOf(item), item);
      if (onlyWrong && r.fraction === 1) return;
      const li = document.createElement('li');
      const pct = Math.round(r.fraction * 100);
      const tag = `<span class="tag ${pct === 100 ? 'ok' : pct ? 'skip' : 'no'}">${pct}%</span>`;
      li.innerHTML = `<div class="rq"><b class="rn">${i + 1}.</b><span class="rtext"><b>PBQ:</b> ${esc(pbqOf(item).title)}` +
                     ` <span class="muted">(${r.earned} of ${r.total} points)</span></span>${tag}</div>` +
                     PBQUI.reviewHTML(pbqOf(item), item);
      ol.appendChild(li);
      return;
    }
    const q = qOf(item);
    const right = isRight(item);
    if (onlyWrong && right) return;

    const li = document.createElement('li');
    const tag = !item.picked.length ? '<span class="tag skip">no answer</span>'
              : right ? '<span class="tag ok">correct</span>'
                      : '<span class="tag no">missed</span>';
    const opts = item.order.map((orig, pos) => {
      const isAnswer = q.answer.includes(orig);
      const chosen = item.picked.includes(orig);
      const cls = isAnswer ? 'correct' : (chosen ? 'chosen-wrong' : '');
      const mark = isAnswer ? '✓' : (chosen ? '✗' : '');
      return `<li class="${cls}"><span class="mark">${mark || ' '}</span>` +
             `<span>${LETTERS[pos]}. ${esc(q.options[orig])}</span></li>`;
    }).join('');

    // number by position in the exam, so filtering does not renumber
    const why = q.explanation
      ? `<p class="why"><span class="why-label">Why</span>${esc(q.explanation)}</p>` : '';
    li.innerHTML = `<div class="rq"><b class="rn">${i + 1}.</b>` +
                   `<span class="rtext">${reviewText(q)}</span>${tag}</div><ul>${opts}</ul>${why}`;
    ol.appendChild(li);
  });

  if (!ol.children.length) {
    ol.innerHTML = '<li class="muted">Nothing missed on this attempt.</li>';
  }
}

/* ── home screen ─────────────────────────────────────── */
function renderHome() {
  $('who').textContent = profile ? `Signed in as ${profile}` : '';
  $('foot-count').textContent = BANK.length;
  $('spec-bank').textContent = BANK.length;
  $('st-total').textContent = BANK.length;

  const pending = load(KEY.exam(profile), null);
  $('btn-resume').hidden = !(profile && pending && !pending.finished && pending.deadline > Date.now());

  const card = $('stats-card');
  if (!profile) { card.hidden = true; return; }

  const ids = BANK.map((q) => q.id);
  const seen = ids.filter((id) => stats[id] && stats[id].seen);
  const weak = ids.filter(isWeak);
  const mastered = seen.filter((id) => stats[id].streak >= CONFIG.MASTERY_STREAK);
  const h = history();

  card.hidden = !(seen.length || h.length);
  $('st-attempts').textContent = h.length;
  $('st-seen').textContent = seen.length;
  $('st-weak').textContent = weak.length;
  $('st-mastered').textContent = mastered.length;
  const pcts = h.map((r) => Math.round((r.score / r.total) * 100));
  $('st-best').textContent = pcts.length ? Math.max(...pcts) + '%' : '–';
  $('st-last').textContent = pcts.length ? pcts[pcts.length - 1] + '%' : '–';

  // a one-bar chart reads as a glitch, so it only appears once there is a trend
  const noTrend = pcts.length < 2;
  $('history').hidden = noTrend;
  document.querySelector('.hist-title').hidden = noTrend;
  $('history').innerHTML = pcts.slice(-24)
    .map((p) => `<i style="height:${Math.max(p, 3)}%" title="${p}%"></i>`).join('');

  $('weak-count').textContent = weak.length;
  $('weak-items').innerHTML = weak.map((id) => {
    const s = stats[id];
    return `<li><span class="misses">missed ${s.wrong}×</span> — ${esc(BY_ID.get(id).text.slice(0, 120))}…</li>`;
  }).join('') || '<li>Nothing outstanding — nice work.</li>';
}

/* ──────────────────────────────────────────────────────────────
 * Modal
 * ────────────────────────────────────────────────────────────── */
let modalAction = null;
function openModal(title, body, okLabel, fn) {
  $('modal-title').textContent = title;
  $('modal-body').textContent = body;
  $('modal-ok').textContent = okLabel;
  modalAction = fn;
  $('modal').hidden = false;
}
function closeModal() { $('modal').hidden = true; modalAction = null; }

/* ──────────────────────────────────────────────────────────────
 * Profile
 * ────────────────────────────────────────────────────────────── */
function setProfile(name) {
  profile = name.trim();
  if (!profile) return false;
  localStorage.setItem(KEY.last, profile);
  stats = load(KEY.stats(profile), {});
  return true;
}

function beginExam(resume) {
  if (!setProfile($('profile-input').value)) {
    $('profile-input').focus();
    return;
  }
  if (resume) {
    exam = load(KEY.exam(profile), null);
    if (!exam || exam.deadline <= Date.now()) { exam = null; }
  }
  if (exam) {                              // drop questions removed from the bank since the exam began
    exam.items = exam.items.filter((it) => (isPbq(it) ? PBQ_BY_ID.has(it.id) : BY_ID.has(it.id)));
    exam.idx = Math.min(exam.idx, exam.items.length - 1);
    if (!exam.items.length) exam = null;
  }
  if (!exam) newExam($('opt-shuffle').checked);

  $('who').textContent = `Signed in as ${profile}`;
  show('exam');
  renderQuestion();
  startTimer();
}

function confirmSubmit() {
  const blank = exam.items.filter((it) => !isAnswered(it)).length;
  const flagged = exam.items.filter((it) => it.flagged).length;
  const bits = [];
  if (blank) bits.push(`${blank} unanswered`);
  if (flagged) bits.push(`${flagged} still flagged`);
  openModal(
    'Submit exam?',
    bits.length ? `You have ${bits.join(' and ')}. Unanswered questions are marked wrong.`
                : 'All questions are answered. Your score is final once you submit.',
    'Submit',
    gradeAndFinish
  );
}

/* ──────────────────────────────────────────────────────────────
 * Import / export
 * ────────────────────────────────────────────────────────────── */
function exportProgress() {
  const blob = new Blob([JSON.stringify({
    app: 'netplus-adaptive-exam', version: 1, profile,
    stats, history: history(), exported: new Date().toISOString(),
  }, null, 1)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `netplus-progress-${profile || 'student'}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function importProgress(file) {
  const reader = new FileReader();
  reader.onload = () => {
    let data;
    try { data = JSON.parse(reader.result); }
    catch { alert('That file is not valid progress data.'); return; }
    if (data.app !== 'netplus-adaptive-exam' || !data.stats) {
      alert('That file is not a Network+ progress export.');
      return;
    }
    if (!profile) setProfile(data.profile || 'imported');
    $('profile-input').value = profile;
    stats = data.stats;
    persistStats();
    if (Array.isArray(data.history)) save(KEY.hist(profile), data.history);
    renderHome();
    alert(`Progress imported for "${profile}".`);
  };
  reader.readAsText(file);
}

/* ──────────────────────────────────────────────────────────────
 * Events
 * ────────────────────────────────────────────────────────────── */
function wire() {
  $('btn-start').addEventListener('click', () => beginExam(false));
  $('btn-resume').addEventListener('click', () => beginExam(true));
  $('profile-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') beginExam(false); });
  $('profile-input').addEventListener('input', () => {
    const name = $('profile-input').value.trim();
    if (name) { setProfile(name); renderHome(); }
  });

  $('btn-prev').addEventListener('click', () => goTo(exam.idx - 1));
  $('btn-next').addEventListener('click', () => goTo(exam.idx + 1));
  $('btn-clear').addEventListener('click', () => {
    const item = current();
    if (!isPbq(item)) { item.picked = []; persistExam(); renderQuestion(); return; }
    openModal('Reset this PBQ?', 'This clears every setting and placement you made in this PBQ.', 'Reset', () => {
      item.ans = {}; item.place = {}; item.term = {};
      persistExam(); renderQuestion();
    });
  });
  $('btn-flag').addEventListener('click', () => {
    current().flagged = !current().flagged;
    persistExam();
    renderQuestion();
  });
  $('btn-submit').addEventListener('click', confirmSubmit);

  $('btn-again').addEventListener('click', () => { exam = null; show('home'); renderHome(); beginExam(false); });
  $('btn-home').addEventListener('click', () => { exam = null; renderHome(); show('home'); });
  $('only-wrong').addEventListener('change', renderReview);

  $('btn-export').addEventListener('click', exportProgress);
  $('btn-import').addEventListener('click', () => $('file-import').click());
  $('file-import').addEventListener('change', (e) => {
    if (e.target.files[0]) importProgress(e.target.files[0]);
    e.target.value = '';
  });
  $('btn-reset').addEventListener('click', () => openModal(
    'Reset progress?',
    `This erases every answer history for "${profile}" on this browser. It cannot be undone.`,
    'Erase it', () => {
      localStorage.removeItem(KEY.stats(profile));
      localStorage.removeItem(KEY.hist(profile));
      localStorage.removeItem(KEY.exam(profile));
      stats = {};
      closeModal();
      renderHome();
    }));

  $('modal-ok').addEventListener('click', () => { const fn = modalAction; closeModal(); if (fn) fn(); });
  $('modal-cancel').addEventListener('click', closeModal);

  document.addEventListener('keydown', (e) => {
    if (!$('modal').hidden && e.key === 'Escape') return closeModal();
    if ($('view-exam').hidden || /^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(e.target.tagName)) return;
    if (!$('modal').hidden || document.querySelector('.pbq-overlay:not([hidden])')) return;
    if (e.key === 'ArrowLeft') goTo(exam.idx - 1);
    else if (e.key === 'ArrowRight') goTo(exam.idx + 1);
    else if (e.key.toLowerCase() === 'f') { current().flagged = !current().flagged; persistExam(); renderQuestion(); }
    else if (/^[1-6]$/.test(e.key) && !isPbq(current())) {
      const pos = Number(e.key) - 1;
      const item = current();
      if (pos < item.order.length) choose(item.order[pos]);
    }
  });

  // A refresh mid-exam must not cost the student their answers or their clock.
  window.addEventListener('beforeunload', (e) => {
    if (exam && !exam.finished) { e.preventDefault(); e.returnValue = ''; }
  });
}

/* ──────────────────────────────────────────────────────────────
 * Init
 * ────────────────────────────────────────────────────────────── */
async function init() {
  try {
    const res = await fetch('data/questions.json', { cache: 'no-cache' });
    const data = await res.json();
    BANK = data.questions;
    BY_ID = new Map(BANK.map((q) => [q.id, q]));
    try {                                  // PBQs are optional: without them exams are all multiple choice
      const pr = await fetch('data/pbqs.json', { cache: 'no-cache' });
      PBQS = ((await pr.json()) || {}).pbqs || [];
    } catch { PBQS = []; }
    PBQ_BY_ID = new Map(PBQS.map((p) => [p.id, p]));
  } catch (e) {
    $('view-home').innerHTML =
      '<section class="card"><h1>Could not load the question bank</h1>' +
      '<p>Open this page over http:// or https:// (GitHub Pages, or a local web server) — ' +
      'browsers block <code>fetch</code> on <code>file://</code> URLs.</p></section>';
    return;
  }

  wire();
  const last = localStorage.getItem(KEY.last);
  if (last) { $('profile-input').value = last; setProfile(last); }
  renderHome();
}

init();
