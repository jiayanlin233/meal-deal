/* ============================================================
   MEAL DEAL RATER — App Logic
   ============================================================ */

let DATA = null;
let reelState = {
  main:  { items: [], index: 0 },
  snack: { items: [], index: 0 },
  drink: { items: [], index: 0 },
};

const ITEM_HEIGHT = 52; // px — matches CSS .reel-item height

// ============================================================
// INIT
// ============================================================
async function init() {
  try {
    const res = await fetch('data.json');
    DATA = await res.json();
  } catch (e) {
    console.error('Failed to load data.json:', e);
    document.body.innerHTML = '<div style="color:#ff4d4d;font-family:monospace;padding:40px;text-align:center">ERROR: Could not load data.json<br>Make sure it exists in the docs/ folder.</div>';
    return;
  }

  // Populate reel items
  ['main', 'snack', 'drink'].forEach(cat => {
    reelState[cat].items = DATA.items[cat];
    reelState[cat].index = 0;
    renderReel(cat);
  });

  // Wire up arrow buttons
  document.querySelectorAll('.arrow-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const reel = btn.dataset.reel;
      const dir = btn.dataset.dir;
      scrollReel(reel, dir === 'up' ? -1 : 1);
      playClick();
    });
  });

  // Wire up main buttons
  document.getElementById('btn-rate').addEventListener('click', rateCombo);
  document.getElementById('btn-random').addEventListener('click', randomCombo);

  // Keyboard controls
  document.addEventListener('keydown', handleKeyboard);
}

// ============================================================
// REEL RENDERING
// ============================================================
function renderReel(cat) {
  const track = document.getElementById(`track-${cat}`);
  const items = reelState[cat].items;

  track.innerHTML = items.map((item, i) => {
    const active = i === reelState[cat].index ? ' active' : '';
    return `<div class="reel-item${active}">${formatItemName(item)}</div>`;
  }).join('');

  updateReelPosition(cat, false);
}

function formatItemName(name) {
  // Capitalize each word for display
  return name.replace(/\b\w/g, c => c.toUpperCase());
}

function updateReelPosition(cat, animate = true) {
  const track = document.getElementById(`track-${cat}`);
  const offset = -reelState[cat].index * ITEM_HEIGHT;
  track.style.transition = animate ? 'transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)' : 'none';
  track.style.transform = `translateY(${offset}px)`;

  // Update active class
  const items = track.querySelectorAll('.reel-item');
  items.forEach((el, i) => {
    el.classList.toggle('active', i === reelState[cat].index);
  });
}

function scrollReel(cat, direction) {
  const len = reelState[cat].items.length;
  let newIndex = reelState[cat].index + direction;

  // Wrap around
  if (newIndex < 0) newIndex = len - 1;
  if (newIndex >= len) newIndex = 0;

  reelState[cat].index = newIndex;
  updateReelPosition(cat, true);

  // Hide result panels when selection changes
  hideResults();
}

// ============================================================
// KEYBOARD CONTROLS
// ============================================================
function handleKeyboard(e) {
  switch(e.key) {
    case 'q': case 'Q': scrollReel('main', -1); playClick(); break;
    case 'a': case 'A': scrollReel('main', 1); playClick(); break;
    case 'w': case 'W': scrollReel('snack', -1); playClick(); break;
    case 's': case 'S': scrollReel('snack', 1); playClick(); break;
    case 'e': case 'E': scrollReel('drink', -1); playClick(); break;
    case 'd': case 'D': scrollReel('drink', 1); playClick(); break;
    case 'Enter': case ' ': e.preventDefault(); rateCombo(); break;
    case 'r': case 'R': randomCombo(); break;
  }
}

// ============================================================
// RATING LOGIC
// ============================================================
function getCurrentSelection() {
  return {
    main:  reelState.main.items[reelState.main.index],
    snack: reelState.snack.items[reelState.snack.index],
    drink: reelState.drink.items[reelState.drink.index],
  };
}

function findMatch(selection) {
  // Look for an exact 3-item match in the database
  if (!DATA || !DATA.deals) return null;

  return DATA.deals.find(deal => {
    if (!deal.items) return false;
    return (
      deal.items.main  === selection.main &&
      deal.items.snack === selection.snack &&
      deal.items.drink === selection.drink
    );
  });
}

function findPartialMatches(selection) {
  // Find deals that match 2 out of 3 items
  if (!DATA || !DATA.deals) return [];

  return DATA.deals.filter(deal => {
    if (!deal.items) return false;
    let matches = 0;
    if (deal.items.main  === selection.main)  matches++;
    if (deal.items.snack === selection.snack) matches++;
    if (deal.items.drink === selection.drink) matches++;
    return matches === 2;
  }).slice(0, 3); // max 3 partial matches
}

// ============================================================
// SPIN & DISPLAY
// ============================================================
async function rateCombo() {
  const btn = document.getElementById('btn-rate');
  btn.classList.add('spinning');
  hideResults();

  // Spin animation on all reels
  ['main', 'snack', 'drink'].forEach(cat => {
    document.getElementById(`track-${cat}`).classList.add('spinning');
  });

  // Wait for dramatic effect
  await sleep(800);

  // Stop spinning (staggered)
  for (const cat of ['main', 'snack', 'drink']) {
    document.getElementById(`track-${cat}`).classList.remove('spinning');
    updateReelPosition(cat, false);
    await sleep(200);
  }

  btn.classList.remove('spinning');

  // Look up the combo
  const selection = getCurrentSelection();
  const match = findMatch(selection);

  if (match) {
    showScore(match);
  } else {
    // Check for partial matches
    const partials = findPartialMatches(selection);
    showNoMatch(partials);
  }
}

async function randomCombo() {
  hideResults();

  // Pick a random deal that has items labelled
  const labelled = DATA.deals.filter(d => d.items !== null);
  if (labelled.length === 0) return;

  const deal = labelled[Math.floor(Math.random() * labelled.length)];

  // Spin all reels
  ['main', 'snack', 'drink'].forEach(cat => {
    document.getElementById(`track-${cat}`).classList.add('spinning');
  });

  await sleep(600);

  // Set each reel to the matching item (staggered stop)
  for (const cat of ['main', 'snack', 'drink']) {
    const targetIndex = reelState[cat].items.indexOf(deal.items[cat]);
    if (targetIndex !== -1) {
      reelState[cat].index = targetIndex;
    }
    document.getElementById(`track-${cat}`).classList.remove('spinning');
    updateReelPosition(cat, false);
    playClick();
    await sleep(300);
  }

  await sleep(200);
  showScore(deal);
}

// ============================================================
// SCORE DISPLAY
// ============================================================
async function showScore(deal) {
  const panel = document.getElementById('score-panel');
  const commentsPanel = document.getElementById('comments-panel');
  const digitTens = document.getElementById('digit-tens');
  const digitOnes = document.getElementById('digit-ones');
  const bar = document.getElementById('score-bar');
  const verdict = document.getElementById('score-verdict');
  const meta = document.getElementById('score-meta');

  // Show panel
  panel.classList.add('visible');

  // Animate digits rolling
  const score = deal.score;
  const tens = Math.floor(score);
  const ones = Math.round((score - tens) * 10);

  // Quick roll effect
  let rollCount = 0;
  const rollInterval = setInterval(() => {
    digitTens.textContent = Math.floor(Math.random() * 10);
    digitOnes.textContent = Math.floor(Math.random() * 10);
    rollCount++;
    if (rollCount > 12) {
      clearInterval(rollInterval);
      digitTens.textContent = tens;
      digitOnes.textContent = ones;
    }
  }, 60);

  await sleep(900);

  // Score bar
  const pct = (score / 10) * 100;
  bar.className = 'score-bar';
  if (score < 4) bar.classList.add('low');
  else if (score < 6) bar.classList.add('mid');
  else if (score < 8) bar.classList.add('high');
  else bar.classList.add('elite');
  bar.style.width = pct + '%';

  // Verdict text
  verdict.textContent = getVerdict(score);
  verdict.style.color = getVerdictColor(score);

  // Meta
  const vendorText = deal.vendor && deal.vendor !== 'unknown' ? ` • ${deal.vendor.toUpperCase()}` : '';
  meta.textContent = `${deal.num_ratings} RATINGS${vendorText}`;

  // Comments
  if (deal.top_comments && deal.top_comments.length > 0) {
    showComments(deal);
  }
}

function getVerdict(score) {
  if (score >= 9.5) return '👑 LEGENDARY';
  if (score >= 8.5) return '🔥 ELITE COMBO';
  if (score >= 7.5) return '✨ VERY NICE';
  if (score >= 6.5) return '👍 SOLID CHOICE';
  if (score >= 5.5) return '😐 MID';
  if (score >= 4.0) return '👎 BELOW AVERAGE';
  if (score >= 2.5) return '💀 GRIM';
  return '🚨 WAR CRIME';
}

function getVerdictColor(score) {
  if (score >= 8) return '#56ff8a';
  if (score >= 6) return '#ffe156';
  if (score >= 4) return '#ffa64d';
  return '#ff4d4d';
}

// ============================================================
// COMMENTS DISPLAY
// ============================================================
function showComments(deal) {
  const panel = document.getElementById('comments-panel');
  const list = document.getElementById('comments-list');
  const link = document.getElementById('reddit-link');

  list.innerHTML = deal.top_comments.map(c => {
    const ratingBadge = c.rating !== null && c.rating !== undefined
      ? `<span class="comment-rating">${c.rating}/10</span>`
      : '';
    return `
      <div class="comment-item">
        ${ratingBadge}
        <div class="comment-author">u/${c.author}</div>
        <div class="comment-body">${escapeHtml(c.text)}</div>
      </div>
    `;
  }).join('');

  link.href = deal.permalink || '#';
  link.style.display = deal.permalink ? 'inline-block' : 'none';

  panel.classList.add('visible');
}

// ============================================================
// NO MATCH DISPLAY
// ============================================================
function showNoMatch(partialMatches) {
  const panel = document.getElementById('no-match-panel');
  panel.classList.add('visible');

  // If we have partial matches, suggest them
  if (partialMatches.length > 0) {
    const suggestions = partialMatches.map(d => {
      const items = d.items;
      return `${formatItemName(items.main)} + ${formatItemName(items.snack)} + ${formatItemName(items.drink)} (${d.score}/10)`;
    }).join('<br>');

    document.querySelector('.no-match-sub').innerHTML =
      `CLOSE MATCHES:<br><span style="color:#ffe156;font-size:0.33rem;line-height:2">${suggestions}</span>`;
  } else {
    document.querySelector('.no-match-sub').textContent = 'Try a different combination or hit RANDOM';
  }
}

// ============================================================
// HELPERS
// ============================================================
function hideResults() {
  document.getElementById('score-panel').classList.remove('visible');
  document.getElementById('comments-panel').classList.remove('visible');
  document.getElementById('no-match-panel').classList.remove('visible');

  // Reset score display
  document.getElementById('digit-tens').textContent = '-';
  document.getElementById('digit-ones').textContent = '-';
  document.getElementById('score-bar').style.width = '0%';
  document.getElementById('score-verdict').textContent = '';
  document.getElementById('score-meta').textContent = '';
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Simple click sound using Web Audio API (no external files needed)
let audioCtx = null;
function playClick() {
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.frequency.value = 660;
    osc.type = 'square'; // pixel-art = square waves!
    gain.gain.value = 0.05;
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.06);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.06);
  } catch (e) {
    // Audio not supported — no problem
  }
}

// ============================================================
// GO!
// ============================================================
document.addEventListener('DOMContentLoaded', init);