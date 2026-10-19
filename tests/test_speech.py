"""Browser regression tests. Run against a local server (default port 8001).
Uses real audio fetch/decode/playback; cannot assess perceived pronunciation.
"""
import hashlib,json,sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
BASE=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8001'
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'audio/th/manifest.json').read_text())
for key,entry in manifest['files'].items():
    assert hashlib.sha256((root/'audio/th'/f'{key}.mp3').read_bytes()).hexdigest()==entry['sha256']
MOCK="""
window.spoken=[];
Object.defineProperty(window,'speechSynthesis',{value:{getVoices:()=>[
 {name:'English',lang:'en-US',voiceURI:'en'}, {name:'Japanese',lang:'ja-JP',voiceURI:'ja'}
],addEventListener:()=>{},cancel:()=>{},speak:u=>{window.spoken.push(u.lang);setTimeout(()=>u.onend?.(),10)}}});
Object.defineProperty(window,'SpeechSynthesisUtterance',{value:class {constructor(text){this.text=text;}}});
"""
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':390,'height':844})
    page.add_init_script(MOCK)
    errors=[]; requests=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('request',lambda request:requests.append(request.url))
    page.goto(BASE)
    page.click('#settingsToggle')
    assert 'เสียงไทยของเว็บ' in page.locator('#voiceSelect').inner_text()
    assert page.evaluate('speechSynthesis.getVoices().every(v=>v.lang!=="th-TH")')
    plans={
      '0':['n-0'], '21':['n-21'], '101':['n-1','hundred','et'],
      '1001':['n-1','thousand','et'],
      'ลบ 99':['minus','n-99'],
      'คำตอบ ลบ 12':['answer-prefix','minus','n-12'],
      'ข้อที่ 5':['question-prefix','n-5'],
      '9999':['n-9','thousand','n-9','hundred','n-99'],
      '989901':['n-9','hundred-thousand','n-8','ten-thousand','n-9','thousand','n-9','hundred','et']}
    for text,expected in plans.items():
        assert page.evaluate('(text)=>KFMAThaiAudio.plan(text)',text)==expected,text
    assert page.evaluate('KFMAThaiAudio.numberParts(1000000)') is None
    for event in ['ready','question','answer','correct','incorrect','complete','timeout']:
        page.select_option('#speechSample',event)
        page.click('#testSpeechBtn')
        page.wait_for_function("document.querySelector('#speechStatus').textContent==='กำลังอ่านด้วยเสียงไทยของเว็บ'",timeout=15000)
        page.click('#stopSpeechBtn')
    assert page.evaluate('spoken.length')==0,'Thai must never call native TTS'
    page.select_option('#speechRate','1.1')
    page.select_option('#speechSample','answer')
    page.click('#testSpeechBtn')
    page.wait_for_function("document.querySelector('#speechStatus').textContent==='อ่านเสียงไทยจบแล้ว'",timeout=15000)
    page.check('#voiceCheck')
    page.fill('#countInput','1');page.fill('#questionCountInput','1');page.fill('#speedInput','100')
    page.reload()
    assert page.locator('#speechRate').input_value()=='1.1'
    page.click('#startBtn')
    page.wait_for_function("document.querySelector('#numberDisplay').textContent==='ครบ 1 ข้อแล้ว'",timeout=15000)
    page.click('#resetBtn')
    assert page.locator('#numberDisplay').inner_text()=='เริ่ม?'
    # Every MP3 must actually decode in the target browser, not just have a file extension.
    decoded=page.evaluate("""async () => {
      const context=new AudioContext();
      let count=0;
      for (const key of Object.keys(KFMAThaiAudioManifest.files)) {
        const r=await fetch('audio/th/'+key+'.mp3'); if(!r.ok) throw Error(key);
        const buffer=await context.decodeAudioData(await r.arrayBuffer());
        if(buffer.duration<=0 || !buffer.getChannelData(0).some(v=>Math.abs(v)>0.001)) throw Error('silent '+key);
        count++;
      }
      await context.close();return count;
    }""")
    assert decoded==len(manifest['files'])
    for lang in ['en-US','ja-JP']:
        result=page.evaluate("""async lang=>{
          const s=new KFMASpeech.Speaker();s.enabled=true;s.lang=lang;
          await s.speak('123');return spoken.at(-1);
        }""",lang)
        assert result==lang
    # Missing files must report the failure and leave a retry possible.
    page.route('**/audio/th/plus.mp3',lambda route:route.fulfill(status=404,body='missing'))
    result=page.evaluate("""async()=>{
      let status='';const s=new KFMAThaiAudio.ThaiAudio(text=>status=text);
      await s.speak('บวก',0.9,0.8);return status;
    }""")
    assert 'ไม่สำเร็จ' in result
    assert not errors,errors
    assert all(urlparse(u).netloc==urlparse(BASE).netloc for u in requests),'External runtime request'
    browser.close()
print(f'PASS: {decoded} real MP3s decoded; Thai playback without an OS Thai voice; 7 samples; number grammar; full game; settings; cancellation; missing-file handling; English/Japanese preserved; no external requests.')
