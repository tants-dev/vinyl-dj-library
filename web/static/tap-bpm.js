(function () {
  var RESET_GAP_MS = 2000; // longer than this since the last tap = new count
  var MAX_TAPS_REMEMBERED = 8; // rolling window, smooths out human timing jitter

  var tapTimestamps = [];

  var bpmEl = document.getElementById("tap-bpm-value");
  var countEl = document.getElementById("tap-count");
  var tapButton = document.getElementById("tap-button");
  var resetButton = document.getElementById("tap-reset");

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
      return;
    }

    var intervals = [];
    for (var i = 1; i < tapTimestamps.length; i++) {
      intervals.push(tapTimestamps[i] - tapTimestamps[i - 1]);
    }
    var avgIntervalMs = intervals.reduce(function (a, b) { return a + b; }, 0) / intervals.length;
    var bpm = 60000 / avgIntervalMs;
    bpmEl.textContent = bpm.toFixed(1);
  }

  function reset() {
    tapTimestamps = [];
    render();
  }

  tapButton.addEventListener("click", registerTap);
  resetButton.addEventListener("click", reset);

  document.addEventListener("keydown", function (e) {
    if (e.code === "Space" && document.activeElement !== resetButton) {
      e.preventDefault();
      registerTap();
    }
  });
})();
