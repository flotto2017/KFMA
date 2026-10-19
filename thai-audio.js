/* Plays bundled Thai MP3s. No installed OS voice, API, or model download needed. */
(function () {
  'use strict';
  const base = new URL('audio/th/', document.currentScript.src);
  const manifest = window.KFMAThaiAudioManifest;
  function numberParts(value) {
    const n = Number(value);
    if (!Number.isSafeInteger(n) || Math.abs(n) > 999999) return null;
    const parts = n < 0 ? ['minus'] : [];
    let remainder = Math.abs(n);
    if (remainder < 100) return parts.concat('n-' + remainder);
    for (const [place, name] of [[100000, 'hundred-thousand'], [10000, 'ten-thousand'], [1000, 'thousand'], [100, 'hundred']]) {
      const digit = Math.floor(remainder / place);
      if (digit) parts.push('n-' + digit, name);
      remainder %= place;
    }
    if (remainder) parts.push(remainder === 1 ? 'et' : 'n-' + remainder);
    return parts;
  }
  function plan(text) {
    text = String(text).trim();
    if (manifest.phrases[text]) return [manifest.phrases[text]];
    if (/^-?\d+$/.test(text)) return numberParts(text);
    let match = text.match(/^(ลบ|บวก)\s+(\d+)$/);
    if (match) { const parts = numberParts(match[2]); return parts && [match[1] === 'ลบ' ? 'minus' : 'plus', ...parts]; }
    match = text.match(/^ข้อที่\s+(\d+)$/);
    if (match) { const parts = numberParts(match[1]); return parts && ['question-prefix', ...parts]; }
    match = text.match(/^คำตอบ(?:คือ)?\s+(ลบ\s+)?(-?\d+)$/);
    if (match) { const parts = numberParts((match[1] ? '-' : '') + match[2]); return parts && ['answer-prefix', ...parts]; }
    match = text.match(/^จบรอบแล้ว ทำครบ (\d+) ข้อ ขอบคุณที่ตั้งใจฝึกนะ$/);
    if (match) { const parts = numberParts(match[1]); return parts && ['complete-prefix', ...parts, 'complete-suffix']; }
    return null;
  }
  class ThaiAudio {
    constructor(onStatus) {
      this.onStatus = onStatus;
      this.context = null;
      this.cache = new Map();
      this.sources = [];
      this.version = 0;
      this.finish = null;
    }
    get supported() { return !!(window.AudioContext || window.webkitAudioContext); }
    cancel() {
      this.version++;
      for (const source of this.sources) { try { source.stop(); } catch (_) {} }
      this.sources = [];
      if (this.finish) this.finish();
    }
    buffer(key) {
      if (!this.cache.has(key)) {
        const pending = fetch(new URL(key + '.mp3', base)).then(response => {
          if (!response.ok) throw new Error('audio-file');
          return response.arrayBuffer();
        }).then(data => this.context.decodeAudioData(data)).catch(error => {
          this.cache.delete(key); // Allow retry after a transient connection failure.
          throw error;
        });
        this.cache.set(key, pending);
      }
      return this.cache.get(key);
    }
    speak(text, rate, volume) {
      this.cancel();
      const version = this.version;
      const parts = plan(text);
      if (!parts || parts.some(key => !manifest.files[key])) {
        this.onStatus('ยังไม่มีไฟล์เสียงไทยสำหรับข้อความนี้');
        return Promise.resolve();
      }
      if (!this.supported) {
        this.onStatus('เบราว์เซอร์นี้เล่นเสียงไม่ได้ กรุณาเปิดใน Chrome, Edge หรือ Safari');
        return Promise.resolve();
      }
      // Resume during the user's click, before any network/decode awaits.
      const Context = window.AudioContext || window.webkitAudioContext;
      let resume;
      try {
        if (!this.context) this.context = new Context();
        resume = this.context.resume();
      } catch (_) {
        this.onStatus('เปิดเสียงไม่ได้ กรุณากดฟังตัวอย่างอีกครั้งใน Chrome, Edge หรือ Safari');
        return Promise.resolve();
      }
      this.onStatus('กำลังโหลดเสียงไทยของเว็บ');
      return new Promise(resolve => {
        let done = false;
        let watchdog;
        const finish = () => {
          if (done) return;
          done = true;
          clearTimeout(watchdog);
          if (this.finish === finish) this.finish = null;
          resolve();
        };
        this.finish = finish;
        watchdog = setTimeout(() => {
          if (version !== this.version) return;
          this.onStatus('โหลดหรือเล่นเสียงไม่สำเร็จ กรุณากดฟังตัวอย่างเพื่อลองใหม่');
          this.cancel();
        }, 30000);
        Promise.all([resume, ...parts.map(key => this.buffer(key))]).then(([, ...buffers]) => {
          if (done || version !== this.version) return;
          if (this.context.state !== 'running') throw new Error('not-allowed');
          const gain = this.context.createGain();
          gain.gain.value = Math.max(0, Math.min(1, Number(volume) || 0));
          gain.connect(this.context.destination);
          const speed = Math.max(0.5, Math.min(2, Number(rate) || 0.9));
          let time = this.context.currentTime + 0.02;
          this.sources = buffers.map((buffer, index) => {
            const source = this.context.createBufferSource();
            source.buffer = buffer;
            source.playbackRate.value = speed;
            source.connect(gain);
            source.onended = () => {
              source.disconnect();
              if (index === buffers.length - 1) {
                gain.disconnect();
                if (!done && version === this.version) {
                  this.sources = [];
                  this.onStatus('อ่านเสียงไทยจบแล้ว');
                  finish();
                }
              }
            };
            source.start(time);
            time += buffer.duration / speed;
            return source;
          });
          this.onStatus('กำลังอ่านด้วยเสียงไทยของเว็บ');
        }).catch(() => {
          if (done || version !== this.version) return;
          this.onStatus('เล่นไฟล์เสียงไทยไม่สำเร็จ กรุณาตรวจอินเทอร์เน็ตแล้วกดฟังตัวอย่างอีกครั้ง');
          this.cancel();
        });
      });
    }
  }
  window.KFMAThaiAudio = {ThaiAudio, plan, numberParts};
})();
