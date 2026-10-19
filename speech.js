/* Bundled Thai audio; native browser speech for the other languages. */
(function () {
  'use strict';
  const messages = {
    ready: 'พร้อมแล้วนะ ตั้งใจฟังโจทย์ แล้วค่อย ๆ คิด',
    start: 'เริ่มได้เลย',
    correct: ['ถูกต้อง เก่งมากเลย', 'เยี่ยมมาก คิดได้ถูกต้องแล้ว', 'ทำได้แล้ว ฝึกต่อไปนะ'],
    incorrect: ['ไม่เป็นไรนะ ลองคิดทีละขั้นอีกครั้ง', 'ข้อนี้ยังไม่ถูก มาลองใหม่ด้วยกันนะ', 'ค่อย ๆ คิดนะ ทุกครั้งที่ฝึก เราเรียนรู้เพิ่มขึ้น'],
    complete: 'จบรอบแล้ว ทำครบ {count} ข้อ ขอบคุณที่ตั้งใจฝึกนะ',
    timeout: 'หมดเวลาแล้ว ขอบคุณที่ตั้งใจฝึก พักสักนิดแล้วลองใหม่ได้นะ',
    question: 'ข้อที่ {count}',
    answer: 'คำตอบคือ {answer}',
    prompt: 'คำตอบเท่าไร ลองคิดดูนะ'
  };
  function message(event, values = {}) {
    let text = messages[event];
    if (!text) throw new Error('Unknown speech event: ' + event);
    if (Array.isArray(text)) text = text[Math.floor(Math.random() * text.length)];
    return text.replace(/\{(\w+)\}/g, (_, key) => String(values[key] ?? ''));
  }
  const languageCode = lang => String(lang || '').toLowerCase().replace(/_/g, '-').split('-')[0];
  class Speaker {
    constructor(onStatus = () => {}) {
      this.onStatus = onStatus;
      this.enabled = false;
      this.lang = 'th-TH';
      this.voiceURI = '';
      this.rate = 0.9;
      this.volume = 0.8;
      this.finish = null;
      this.thaiAudio = new KFMAThaiAudio.ThaiAudio(onStatus);
    }
    get nativeSupported() { return !!window.speechSynthesis && typeof window.SpeechSynthesisUtterance === 'function'; }
    get supported() { return languageCode(this.lang) === 'th' ? this.thaiAudio.supported : this.nativeSupported; }
    voices() {
      if (languageCode(this.lang) === 'th') return this.thaiAudio.supported ? [{name: 'เสียงไทยของเว็บ (ไม่ต้องติดตั้ง)', lang: 'th-TH', voiceURI: 'kfma-thai-files', default: true}] : [];
      return this.nativeSupported ? window.speechSynthesis.getVoices().filter(v =>
        languageCode(v.lang) === languageCode(this.lang)) : [];
    }
    cancel() {
      this.thaiAudio.cancel();
      if (this.finish) this.finish();
      if (this.nativeSupported) window.speechSynthesis.cancel();
    }
    speak(text, {lang = this.lang, preview = false} = {}) {
      this.cancel();
      if (!this.enabled && !preview) return Promise.resolve();
      if (languageCode(lang) === 'th') return this.thaiAudio.speak(text, this.rate, this.volume);
      if (!this.nativeSupported) {
        this.onStatus('เบราว์เซอร์นี้ไม่รองรับเสียงอ่าน ยังเล่นแบบไม่มีเสียงได้');
        return Promise.resolve();
      }
      const voices = window.speechSynthesis.getVoices().filter(v =>
        languageCode(v.lang) === languageCode(lang));
      return new Promise(resolve => {
        const utterance = new SpeechSynthesisUtterance(String(text));
        const voice = voices.find(v => v.voiceURI === this.voiceURI) || voices.find(v => v.default) || voices[0];
        if (voice) utterance.voice = voice;
        utterance.lang = lang;
        utterance.rate = this.rate;
        utterance.volume = this.volume;
        let done = false;
        const finish = () => {
          if (done) return;
          done = true;
          clearTimeout(watchdog);
          if (this.finish === finish) this.finish = null;
          resolve();
        };
        const watchdog = setTimeout(() => {
          finish();
          window.speechSynthesis.cancel();
          this.onStatus('เสียงอ่านไม่ตอบสนอง เล่นต่อโดยไม่มีเสียงข้อความนี้');
        }, 20000);
        this.finish = finish;
        utterance.onstart = () => this.onStatus('กำลังอ่านด้วยเสียง ' + (voice ? voice.name : lang));
        utterance.onend = () => {
          if (!done) this.onStatus('อ่านเสียงจบแล้ว');
          finish();
        };
        utterance.onerror = event => {
          if (done) return;
          if (['language-unavailable', 'voice-unavailable', 'synthesis-unavailable'].includes(event.error)) {
            this.onStatus('อุปกรณ์ยังไม่มีเสียงภาษาที่เลือก กรุณาติดตั้งเสียงภาษานี้ในระบบ แล้วเปิดเว็บใหม่');
          } else if (event.error === 'not-allowed') {
            this.onStatus('เบราว์เซอร์ยังไม่อนุญาตเสียง กรุณากดฟังตัวอย่างอีกครั้ง หรือเปิดเว็บใน Safari / Chrome โดยตรง');
          } else if (!['canceled', 'interrupted'].includes(event.error)) {
            this.onStatus('เล่นเสียงไม่ได้ (' + event.error + ') กรุณาลองทดสอบเสียงอีกครั้ง');
          }
          finish();
        };
        // Keep the utterance alive until the browser finishes speaking.
        this.utterance = utterance;
        try {
          if (window.speechSynthesis.paused) window.speechSynthesis.resume();
          window.speechSynthesis.speak(utterance);
        }
        catch (_) { this.onStatus('เล่นเสียงไม่ได้ ยังเล่นแบบไม่มีเสียงได้'); finish(); }
      });
    }
    event(name, values = {}, options = {}) { return this.speak(message(name, values), {...options, lang: 'th-TH'}); }
  }
  window.KFMASpeech = {Speaker, message};
})();
