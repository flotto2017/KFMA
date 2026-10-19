"""One-time local asset generation. No TTS service is used at website runtime.
Usage: python tools/generate_thai_audio.py /path/to/verified/model-directory
Requires fastthaig2p, numpy, onnxruntime and ffmpeg. See audio/th/README.md.
"""
import hashlib,json,subprocess,sys,tempfile,wave
from pathlib import Path
import numpy as np
from fastthaig2p import TTS

root=Path(__file__).resolve().parents[1]
model=Path(sys.argv[1])
expected={
 'config.json':'ea8e1a52dd433e27d953255d2bf340fc754ec62a60686d112136c4eee603709f',
 'kokoro_thai.onnx':'a41a5ea020919e47df03226aebe72a64833bc666dfd6eeca6744d8c248270038',
 'thai_som.npy':'bdec2300889bd5db59c81a4f0e1604c78124abf6096d6e84d4db1bbeef122240'}
for name,digest in expected.items():
 assert hashlib.sha256((model/name).read_bytes()).hexdigest()==digest,name

digits=['ศูนย์','หนึ่ง','สอง','สาม','สี่','ห้า','หก','เจ็ด','แปด','เก้า']
def number(n):
 if n<10:return digits[n]
 tens,ones=divmod(n,10)
 return (('' if tens==1 else 'ยี่' if tens==2 else digits[tens])+'สิบ'+('เอ็ด' if ones==1 else digits[ones] if ones else ''))
phrases={
 'ready':'พร้อมแล้วนะ ตั้งใจฟังโจทย์ แล้วค่อย ๆ คิด',
 'start':'เริ่มได้เลย',
 'correct-1':'ถูกต้อง เก่งมากเลย',
 'correct-2':'เยี่ยมมาก คิดได้ถูกต้องแล้ว',
 'correct-3':'ทำได้แล้ว ฝึกต่อไปนะ',
 'incorrect-1':'ไม่เป็นไรนะ ลองคิดทีละขั้นอีกครั้ง',
 'incorrect-2':'ข้อนี้ยังไม่ถูก มาลองใหม่ด้วยกันนะ',
 'incorrect-3':'ค่อย ๆ คิดนะ ทุกครั้งที่ฝึก เราเรียนรู้เพิ่มขึ้น',
 'timeout':'หมดเวลาแล้ว ขอบคุณที่ตั้งใจฝึก พักสักนิดแล้วลองใหม่ได้นะ',
 'prompt':'คำตอบเท่าไร ลองคิดดูนะ',
 'question-prefix':'ข้อที่',
 'answer-prefix':'คำตอบคือ',
 'complete-prefix':'จบรอบแล้ว ทำครบ',
 'complete-suffix':'ข้อ ขอบคุณที่ตั้งใจฝึกนะ',
 'minus':'ลบ',
 'plus':'บวก',
 'hundred':'ร้อย','thousand':'พัน','ten-thousand':'หมื่น','hundred-thousand':'แสน',
 'et':'เอ็ด'}
texts={**{f'n-{n}':number(n) for n in range(100)},**phrases}
out=root/'audio'/'th';out.mkdir(parents=True,exist_ok=True)
tts=TTS(model/'kokoro_thai.onnx',model/'thai_som.npy',config_path=model/'config.json',intra_op_threads=3)
manifest={'version':1,'voice':'thai_som','phrases':{},'files':{},'source':{'release':'https://github.com/awslabs/FastThaiG2P/releases/tag/v0.3.0','sha256':expected}}
for i,(key,text) in enumerate(texts.items()):
 path=out/(key+'.mp3')
 if not path.exists():
  audio=tts.generate(text)
  assert np.isfinite(audio).all() and len(audio)>2400 and np.max(np.abs(audio))>0.01,(key,'invalid waveform')
  pcm=(np.clip(audio,-1,1)*32767).astype('<i2')
  with tempfile.NamedTemporaryFile(suffix='.wav') as tmp:
   with wave.open(tmp.name,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(pcm.tobytes())
   subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',tmp.name,'-af','silenceremove=start_periods=1:start_duration=0.01:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_duration=0.01:start_threshold=-50dB,areverse','-codec:a','libmp3lame','-b:a','64k',str(path)],check=True)
 duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)]))
 assert 0.08<duration<25,(key,duration)
 manifest['files'][key]={'text':text,'duration':duration,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 if key in phrases:manifest['phrases'][text]=key
 if i%10==0:print(f'{i+1}/{len(texts)} {key}',flush=True)
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(out/'manifest.js').write_text('window.KFMAThaiAudioManifest = '+json.dumps(manifest,ensure_ascii=False)+';\n')
print('Generated',len(texts),'files;',sum(x.stat().st_size for x in out.glob('*.mp3')),'bytes',flush=True)
