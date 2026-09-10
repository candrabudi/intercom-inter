(() => {
  const byId = (id) => document.getElementById(id);
  const applyPair = (pair, user) => {
    byId(`mic${user}`).value = String(pair.mic_id);
    byId(`speaker${user}`).value = String(pair.speaker_id);
  };
  const loadPairs = async () => {
    try {
      const response = await fetch('/api/devices');
      if (!response.ok) return;
      const { headset_pairs: pairs = [], devices = [] } = await response.json();
      if (pairs[0]) applyPair(pairs[0], 'A');
      if (pairs[1]) applyPair(pairs[1], 'B');
      const summary = byId('deviceSummary');
      if (pairs.length) {
        summary.textContent = `Terdeteksi ${pairs.length} pasangan headset otomatis. Pilihan A dan B sudah diisi.`;
      } else {
        const micCount = devices.filter((item) => item.kind === 'microphone' && item.selectable).length;
        const speakerCount = devices.filter((item) => item.kind === 'speaker' && item.selectable).length;
        summary.textContent = `Terdeteksi ${micCount} microphone dan ${speakerCount} speaker. Pilih manual jika pasangan belum terbaca.`;
      }
    } catch (_) { /* Existing app.js handles the primary device error state. */ }
  };
  document.getElementById('refresh').addEventListener('click', () => setTimeout(loadPairs, 120));
  setTimeout(loadPairs, 180);
})();
