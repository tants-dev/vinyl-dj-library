(function () {
  var RESET_GAP_MS = 2000;
  var MAX_TAPS_REMEMBERED = 8;

  var tapTimestamps = [];
  var currentBpm = null;

  var bpmEl      = document.getElementById("tap-bpm-value");
  var countEl    = document.getElementById("tap-count");
  var tapButton  = document.getElementById("tap-button");
  var resetButton = document.getElementById("tap-reset");
  var useBtn     = document.getElementById("tap-use-btn");

  function registerTap() {
    var now = performance.now();

    if (tapTimestamps.length > 0) {
      var gap = now - tapTimestamps[tapTimestamps.length - 1];
      if (gap > RESET_GAP_MS) {
        tapTimestamps = [];
      }
    }

    tapTimestamps.push(now);
    if (tapTimestamps.length > MAX_TAPS_REMEMBERED) {
      tapTimestamps.shift();
    }

    render();
  }

  function render() {
    countEl.textContent = tapTimestamps.length + (tapTimestamps.length === 1 ? " tap" : " taps");

    if (tapTimestamps.length < 2) {
      bpmEl.textContent = "—";
      currentBpm = null;
      if (useBtn) useBtn.classList.add("hidden");
      return;
    }

    var intervals = [];
    for (var i = 1; i < tapTimestamps.length; i++) {
      intervals.push(tapTimestamps[i] - tapTimestamps[i - 1]);
    }
    var avgIntervalMs = intervals.reduce(function (a, b) { return a + b; }, 0) / intervals.length;
    currentBpm = 60000 / avgIntervalMs;
    bpmEl.textContent = Math.round(currentBpm);
    if (useBtn) useBtn.classList.remove("hidden");
  }

  function reset() {
    tapTimestamps = [];
    currentBpm = null;
    if (useBtn) useBtn.classList.add("hidden");
    render();
  }

  if (useBtn) {
    useBtn.addEventListener("click", function () {
      if (!currentBpm) return;
      var bpmInput = document.getElementById("save-bpm-input");
      var keyInput = document.getElementById("save-key-input");
      var sourceEl = document.getElementById("save-source");
      var saveSection = document.querySelector(".save-section");
      if (bpmInput) bpmInput.value = Math.round(currentBpm);
      if (keyInput) keyInput.value = "";
      if (sourceEl) sourceEl.value = "manual";
      if (saveSection) saveSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
      if (bpmInput) {
        bpmInput.classList.add("save-input-flash");
        setTimeout(function () { bpmInput.classList.remove("save-input-flash"); }, 800);
      }
    });
  }

  tapButton.addEventListener("click", registerTap);
  resetButton.addEventListener("click", reset);

  document.addEventListener("keydown", function (e) {
    var tag = document.activeElement && document.activeElement.tagName;
    if (e.code === "Space" && tag !== "INPUT" && tag !== "TEXTAREA" && document.activeElement !== resetButton) {
      e.preventDefault();
      registerTap();
    }
  });
})();
