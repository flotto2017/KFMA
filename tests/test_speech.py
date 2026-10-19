"""Run against a local Python HTTP server: python3 tests/test_speech.py [base URL].
Speech synthesis is mocked to verify scheduling; audible output needs a real device.
"""
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8001'
MOCK = r"""
window.spoken = [];
window.holdNumbers = false;
window.voiceList = [{name:'Thai test',lang:'th-TH',voiceURI:'thai-test',default:true}];
window.activeSpeech = null;
class Utterance { constructor(text) { this.text=text; } }
Object.defineProperty(window, 'SpeechSynthesisUtterance', {value:Utterance});
Object.defineProperty(window, 'speechSynthesis', {value:{
 getVoices:()=>window.voiceList,
 addEventListener:()=>{},
 cancel:()=>{ clearTimeout(window.speechTimer); window.activeSpeech=null; },
 speak:u=>{
  window.spoken.push({text:u.text,lang:u.lang,rate:u.rate,volume:u.volume});
  window.activeSpeech=u;
  if (!(window.holdNumbers && /^\d+$/.test(u.text)))
   window.speechTimer=setTimeout(()=>{ window.activeSpeech=null; u.onend?.(); },40);
 }
}});
"""
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':390,'height':844})
    errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.add_init_script(MOCK)
    page.goto(BASE)
    page.click('#settingsToggle')
    assert page.locator('#voiceLangSelect').input_value() == 'th-TH'
    page.select_option('#voiceSelect','thai-test')
    page.select_option('#speechRate','0.75')
    for event in ['ready','question','answer','correct','incorrect','complete','timeout']:
        page.select_option('#speechSample',event)
        page.click('#testSpeechBtn')
        page.wait_for_timeout(60)
    spoken=page.evaluate('window.spoken')
    assert len(spoken)==7
    assert all(s['lang']=='th-TH' and s['rate']==0.75 for s in spoken)
    assert '5' in spoken[5]['text'] and '12' in spoken[2]['text']
    page.check('#voiceCheck')
    page.fill('#countInput','1')
    page.fill('#questionCountInput','1')
    page.fill('#speedInput','100')
    page.reload()
    assert page.locator('#voiceSelect').input_value()=='thai-test'
    assert page.locator('#speechRate').input_value()=='0.75'
    page.click('#startBtn')
    page.wait_for_function("document.querySelector('#numberDisplay').textContent==='ครบ 1 ข้อแล้ว'", timeout=15000)
    assert any('จบรอบแล้ว ทำครบ 1 ข้อ' in s['text'] for s in page.evaluate('spoken'))
    # Slow speech must not change the original exercise timing.
    page.evaluate('window.holdNumbers=true')
    page.click('#startBtn')
    page.wait_for_function("window.activeSpeech && /^\\d+$/.test(window.activeSpeech.text)")
    number=page.locator('#numberDisplay').inner_text()
    page.wait_for_timeout(400)
    assert page.locator('#numberDisplay').inner_text()!=number
    page.click('#resetBtn')
    page.wait_for_timeout(150)
    assert page.locator('#numberDisplay').inner_text()=='เริ่ม?'
    assert page.evaluate('window.activeSpeech===null')
    # English/Japanese voices must never be substituted for missing Thai.
    page.evaluate("window.voiceList=[{name:'English',lang:'en-US',voiceURI:'en'},{name:'Japanese',lang:'ja-JP',voiceURI:'ja'}]")
    page.click('#settingsToggle')
    count=page.evaluate('spoken.length')
    page.click('#testSpeechBtn')
    assert page.evaluate('spoken.length') == count
    assert page.evaluate('activeSpeech === null')
    assert 'ไม่พบเสียงภาษาไทย' in page.locator('#speechStatus').inner_text()
    for lang in ['en-US','ja-JP']:
        result=page.evaluate("""async lang => {
          const s=new KFMASpeech.Speaker(); s.enabled=true; s.lang=lang;
          await s.speak('voice test'); return window.spoken.at(-1).lang;
        }""",lang)
        assert result == lang
    page.evaluate('window.voiceList=[]')
    page.click('#testSpeechBtn')
    assert 'ไม่พบเสียงภาษาไทย' in page.locator('#speechStatus').inner_text()
    page.click('#startBtn')
    page.wait_for_function("document.querySelector('#numberDisplay').textContent==='ครบ 1 ข้อแล้ว'", timeout=15000)
    assert not errors, errors
    unsupported=browser.new_page()
    unsupported.add_init_script("Object.defineProperty(window,'speechSynthesis',{value:undefined}); delete window.speechSynthesis;")
    # Locale formats used by some device speech providers must match Thai.
    result = page.evaluate("""async () => {
      window.voiceList=[{name:'Thai underscore',lang:'th_TH',voiceURI:'thai-underscore'}];
      const s=new KFMASpeech.Speaker(); s.enabled=true;
      const matches=s.voices().length;
      await s.speak('ทดสอบ');
      return matches;
    }""")
    assert result == 1
    # A confirmed missing language is reported, rather than silently ignored.
    error = page.evaluate("""async () => {
      const s=new KFMASpeech.Speaker(text=>window.speechError=text);
      s.enabled=true; window.holdNumbers=true;
      const pending=s.speak('123');
      window.activeSpeech.onerror({error:'language-unavailable'});
      await pending; s.cancel();
      return window.speechError;
    }""")
    assert 'ติดตั้งเสียงภาษาไทย' in error
    # Test the adapter's unsupported branch without depending on browser property configurability.
    unsupported.goto(BASE)
    result=unsupported.evaluate("""async () => {
      const s=new KFMASpeech.Speaker(text=>window.lastStatus=text);
      Object.defineProperty(s,'supported',{value:false});
      await s.speak('ทดสอบ',{preview:true});
      return window.lastStatus;
    }""")
    assert 'ไม่รองรับ' in result
    browser.close()
print('PASS: 7 speech events, settings persistence, full game, unchanged exercise timing, reset cancellation, missing voices, unsupported adapter; no JavaScript errors.')
