(function () {
  const recordBtn   = document.getElementById('clip-record-btn');
  const timerEl     = document.getElementById('clip-timer');
  const errorEl     = document.getElementById('clip-error');
  const resultEl    = document.getElementById('clip-result');
  const bpmDisplay  = document.getElementById('clip-bpm-display');
  const keyDisplay  = document.getElementById('clip-key-display');
  const confDisplay = document.getElementById('clip-conf-display');
  const clearBtn    = document.getElementById('clip-clear-btn');
  const bpmHalfBtn  = document.getElementById('clip-bpm-half');
  const bpmDblBtn   = document.getElementById('clip-bpm-double');
  const searchInput = document.getElementById('clip-track-search');
  const resultsEl   = document.getElementById('clip-track-results');

  // Shared save section
  const saveBpmInput = document.getElementById('save-bpm-input');
  const saveKeyInput = document.getElementById('save-key-input');
  const saveSourceEl = document.getElementById('save-source');
  const presetBtn    = document.getElementById('clip-preset-btn');

  const MAX_SECONDS = 30;

  // Reverse Camelot map — lets the user type "3B" and have it save as "Db major"
  const CAMELOT_TO_KEY = {
    "1B":"B major",  "1A":"G# minor",
    "2B":"F# major", "2A":"D# minor",
    "3B":"Db major", "3A":"Bb minor",
    "4B":"Ab major", "4A":"F minor",
    "5B":"Eb major", "5A":"C minor",
    "6B":"Bb major", "6A":"G minor",
    "7B":"F major",  "7A":"D minor",
    "8B":"C major",  "8A":"A minor",
    "9B":"G major",  "9A":"E minor",
    "10B":"D major", "10A":"B minor",
    "11B":"A major", "11A":"F# minor",
    "12B":"E major", "12A":"C# minor",
  };

  let audioCtx      = null;
  let sourceNode    = null;
  let processorNode = null;
  let stream        = null;
  let sampleChunks  = [];
  let sampleRate    = 44100;
  let timerInterval = null;
  let elapsed       = 0;
  let currentResult = null;

  // Read preset track injected by the template when arriving via /tap-bpm?track_id=X
  const presetEl = document.getElementById('clip-preset-track');
  const presetTrack = presetEl ? {
    id: parseInt(presetEl.dataset.id),
    title: presetEl.dataset.title,
    artist: presetEl.dataset.artist,
    existing_bpm: presetEl.dataset.existingBpm ? parseFloat(presetEl.dataset.existingBpm) : null,
    existing_key: presetEl.dataset.existingKey || null,
  } : null;

  if (presetBtn) {
    presetBtn.addEventListener('click', function () {
      assignToTrack(presetTrack.id, presetBtn, presetTrack);
    });
  }

  // --- WAV encoding -------------------------------------------------------

  function encodeWAV(chunks, sr) {
    const totalLen = chunks.reduce(function (n, c) { return n + c.length; }, 0);
    const samples  = new Float32Array(totalLen);
    let pos = 0;
    chunks.forEach(function (c) { samples.set(c, pos); pos += c.length; });

    const buf  = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buf);

    function str(off, s) {
      for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
    }

    str(0,  'RIFF');
    view.setUint32( 4, 36 + samples.length * 2, true);
    str(8,  'WAVE');
    str(12, 'fmt ');
    view.setUint32(16, 16,       true);
    view.setUint16(20,  1,       true);
    view.setUint16(22,  1,       true);
    view.setUint32(24, sr,       true);
    view.setUint32(28, sr * 2,   true);
    view.setUint16(32,  2,       true);
    view.setUint16(34, 16,       true);
    str(36, 'data');
    view.setUint32(40, samples.length * 2, true);

    let off = 44;
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      off += 2;
    }

    return new Blob([buf], { type: 'audio/wav' });
  }

  // --- UI helpers ---------------------------------------------------------

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.classList.remove('hidden');
  }
  function clearError() {
    errorEl.textContent = '';
    errorEl.classList.add('hidden');
  }
  function resetBtn() {
    recordBtn.textContent = '● Record';
    recordBtn.disabled = false;
    recordBtn.classList.remove('recording');
    timerEl.classList.add('hidden');
    timerEl.textContent = '0s';
    elapsed = 0;
  }

  function syncSaveBpm(bpm) {
    if (saveBpmInput) saveBpmInput.value = Math.round(bpm);
    if (saveSourceEl) saveSourceEl.value = 'local_analysis';
  }

  // --- Recording ----------------------------------------------------------

  async function startRecording() {
    clearError();
    sampleChunks = [];

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    } catch (_) {
      showError('Microphone access denied. Allow mic access and try again.');
      return;
    }

    audioCtx      = new AudioContext();
    sampleRate    = audioCtx.sampleRate;
    sourceNode    = audioCtx.createMediaStreamSource(stream);
    processorNode = audioCtx.createScriptProcessor(4096, 1, 1);

    processorNode.onaudioprocess = function (e) {
      sampleChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    };
    sourceNode.connect(processorNode);
    processorNode.connect(audioCtx.destination);

    recordBtn.textContent = '⏹ Stop';
    recordBtn.classList.add('recording');
    timerEl.classList.remove('hidden');
    elapsed = 0;
    timerInterval = setInterval(function () {
      elapsed++;
      timerEl.textContent = elapsed + 's';
      if (elapsed >= MAX_SECONDS) stopRecording();
    }, 1000);
  }

  function stopRecording() {
    clearInterval(timerInterval);
    timerInterval = null;

    if (sourceNode)    { sourceNode.disconnect(); sourceNode = null; }
    if (processorNode) { processorNode.disconnect(); processorNode = null; }
    if (stream)        { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    if (audioCtx)      { audioCtx.close(); audioCtx = null; }

    recordBtn.textContent = '▶ Analysing…';
    recordBtn.disabled = true;
    recordBtn.classList.remove('recording');
    timerEl.classList.add('hidden');

    sendClip(encodeWAV(sampleChunks, sampleRate));
  }

  function clearResult() {
    currentResult = null;
    resultEl.classList.add('hidden');
    if (saveBpmInput) saveBpmInput.value = '';
    if (saveKeyInput) saveKeyInput.value = '';
    if (saveSourceEl) saveSourceEl.value = 'manual';
    searchInput.value = '';
    resultsEl.innerHTML = '';
    if (presetBtn) { presetBtn.textContent = 'Save'; presetBtn.disabled = false; presetBtn.style.background = ''; }
  }

  recordBtn.addEventListener('click', function () {
    if (audioCtx) { stopRecording(); } else { startRecording(); }
  });

  if (clearBtn) clearBtn.addEventListener('click', clearResult);

  function adjustBpm(factor) {
    if (!currentResult) return;
    currentResult.bpm = Math.round(currentResult.bpm * factor);
    bpmDisplay.value = currentResult.bpm;
    syncSaveBpm(currentResult.bpm);
  }
  if (bpmHalfBtn) bpmHalfBtn.addEventListener('click', function () { adjustBpm(0.5); });
  if (bpmDblBtn)  bpmDblBtn.addEventListener('click',  function () { adjustBpm(2); });
  if (bpmDisplay) bpmDisplay.addEventListener('input', function () {
    if (currentResult) {
      currentResult.bpm = parseFloat(bpmDisplay.value) || currentResult.bpm;
      syncSaveBpm(currentResult.bpm);
    }
  });

  // --- Upload & result ----------------------------------------------------

  async function sendClip(blob) {
    const form = new FormData();
    form.append('file', blob, 'clip.wav');

    let data;
    try {
      const resp = await fetch('/analyze-clip', { method: 'POST', body: form });
      if (!resp.ok) {
        const err = await resp.json().catch(function () { return {}; });
        showError('Analysis failed: ' + (err.detail || resp.statusText));
        resetBtn();
        return;
      }
      data = await resp.json();
    } catch (err) {
      showError('Network error: ' + err.message);
      resetBtn();
      return;
    }

    const KEY_CONF_THRESHOLD = 0.45;
    const lowConf = data.confidence != null && data.confidence < KEY_CONF_THRESHOLD;

    if (lowConf) {
      showError(
        'Analysis inconclusive (' + Math.round(data.confidence * 100) + '% key confidence) — ' +
        'try a longer clip in a quieter space.'
      );
      resetBtn();
      return;
    }

    currentResult = data;
    const camelot = data.camelot ? data.camelot + ' · ' : '';
    bpmDisplay.value = Math.round(data.bpm);
    keyDisplay.textContent = camelot + (data.key || '');
    keyDisplay.className = 'clip-key';
    confDisplay.textContent = data.confidence != null
      ? 'Key confidence: ' + Math.round(data.confidence * 100) + '%'
      : '';
    confDisplay.className = 'clip-confidence';
    resultEl.classList.remove('hidden');

    // Populate shared save section — show Camelot in the key field
    syncSaveBpm(data.bpm);
    if (saveKeyInput) saveKeyInput.value = data.camelot || data.key || '';

    searchInput.value = '';
    resultsEl.innerHTML = '';
    if (!presetTrack) searchInput.focus();
    resetBtn();
  }

  // --- Track search & assign ----------------------------------------------

  let searchTimeout = null;
  searchInput.addEventListener('input', function () {
    clearTimeout(searchTimeout);
    const q = searchInput.value.trim();
    if (!q) { resultsEl.innerHTML = ''; return; }
    searchTimeout = setTimeout(function () { doSearch(q); }, 300);
  });

  async function doSearch(q) {
    let tracks;
    try {
      const resp = await fetch('/track-search?q=' + encodeURIComponent(q));
      tracks = await resp.json();
    } catch (_) { return; }

    resultsEl.innerHTML = '';
    if (!tracks.length) {
      resultsEl.innerHTML = '<p style="color:var(--muted);font-size:0.85rem;">No tracks found.</p>';
      return;
    }
    tracks.forEach(function (track) {
      const item = document.createElement('div');
      item.className = 'clip-track-item';
      item.innerHTML =
        '<div class="clip-track-name">' +
          '<span>' + esc(track.title) + '</span>' +
          '<small>' + esc(track.artist) + ' — ' + esc(track.release) + '</small>' +
        '</div>' +
        '<button class="clip-assign-btn" data-id="' + track.id + '">Save</button>';
      item.querySelector('.clip-assign-btn').addEventListener('click', function () {
        assignToTrack(track.id, this, track);
      });
      resultsEl.appendChild(item);
    });
  }

  async function assignToTrack(trackId, btn, track) {
    const bpm = saveBpmInput ? parseFloat(saveBpmInput.value) : null;
    const source = saveSourceEl ? saveSourceEl.value : 'manual';
    // Resolve key: clip analysis stores the standard key in currentResult.key; if the user
    // typed a Camelot code (e.g. "3B") look it up; otherwise pass through as-is.
    const rawKey = saveKeyInput ? saveKeyInput.value.trim() : '';
    const key = (currentResult && currentResult.key)
      ? currentResult.key
      : (CAMELOT_TO_KEY[rawKey.toUpperCase()] || rawKey || null);

    if (!bpm) {
      alert('Record a clip or enter a BPM before saving.');
      return;
    }
    if (track.existing_bpm != null) {
      const msg = 'Overwrite existing data (' + Math.round(track.existing_bpm) + ' BPM' +
        (track.existing_key ? ', ' + track.existing_key : '') + ')?';
      if (!window.confirm(msg)) return;
    }
    btn.disabled = true;
    btn.textContent = '…';

    try {
      const resp = await fetch('/track/' + trackId + '/bpm-key', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bpm, key, source }),
      });
      btn.textContent = resp.ok ? 'Saved ✓' : 'Error';
      if (resp.ok) btn.style.background = '#16a34a';
      else btn.disabled = false;
    } catch (_) {
      btn.textContent = 'Error';
      btn.disabled = false;
    }
  }

  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
})();
