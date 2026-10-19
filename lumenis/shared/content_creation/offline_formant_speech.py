"""Explicit third-party eSpeak NG formant speech, never a neural-voice fallback."""
import array,hashlib,json,os,re,shutil,subprocess,tempfile,unicodedata,wave
from pathlib import Path
from .video_editing import VideoEditingError

VOICES={'zh-CN':'cmn','ko':'ko','en':'en-us'}


def _runtime():
    binary=os.environ.get('LUMENIS_ESPEAK_BINARY') or shutil.which('espeak-ng')
    if not binary or not Path(binary).is_absolute() or not Path(binary).is_file():raise VideoEditingError('ESPEAK_RUNTIME_UNAVAILABLE')
    environment=dict(os.environ);args=[]
    data=os.environ.get('LUMENIS_ESPEAK_DATA_PARENT')
    libraries=os.environ.get('LUMENIS_ESPEAK_LIBRARY_DIR')
    for value in (data,libraries):
        if value and (not Path(value).is_absolute() or not Path(value).is_dir()):raise VideoEditingError('ESPEAK_CONFIGURATION_INVALID')
    if data:args=['--path='+data]
    if libraries:environment['LD_LIBRARY_PATH']=libraries
    return str(Path(binary).resolve()),args,environment


def synthesize_formant_speech(text,*,language,voice=None,check_cancel=None):
    from .rendering import _run
    from shared_artifacts import _ffmpeg_path
    if not isinstance(language,str) or language not in VOICES:raise VideoEditingError('TTS_LANGUAGE_UNAVAILABLE')
    selected=VOICES[language]
    if voice is not None and voice!=selected:raise VideoEditingError('TTS_VOICE_UNAVAILABLE')
    if (not isinstance(text,str) or not text.strip() or len(text)>4000
            or any(unicodedata.category(c).startswith('C') and c not in '\n\t' for c in text)
            or any(marker in text for marker in ('[[',']]','<','>'))):raise VideoEditingError('TTS_TEXT_INVALID')
    def check():
        if check_cancel:check_cancel()
    check();binary,args,environment=_runtime();binary_hash=hashlib.sha256(Path(binary).read_bytes()).hexdigest();ffmpeg=_ffmpeg_path()
    if not ffmpeg:raise VideoEditingError('MEDIA_RENDER_TOOLS_UNAVAILABLE')
    try:
        voices=subprocess.run([binary,*args,'--voices'],env=environment,capture_output=True,text=True,timeout=10,check=True).stdout
        version=subprocess.run([binary,*args,'--version'],env=environment,capture_output=True,text=True,timeout=10,check=True).stdout.splitlines()[0]
    except (OSError,subprocess.SubprocessError,IndexError) as exc:raise VideoEditingError('ESPEAK_RUNTIME_UNAVAILABLE') from exc
    check()
    languages={line.split()[1] for line in voices.splitlines()[1:] if len(line.split())>2}
    if selected not in languages:raise VideoEditingError('TTS_VOICE_UNAVAILABLE')
    with tempfile.TemporaryDirectory(prefix='lumenis-formant-speech-') as temporary:
        work=Path(temporary);source=work/'source.txt';output=work/'speech.wav';pcm=work/'decoded.pcm'
        source.write_text(text,encoding='utf-8')
        def bounded():
            check()
            if output.exists() and output.stat().st_size>30*1024*1024:raise VideoEditingError('TTS_AUDIO_LIMIT_EXCEEDED')
        _run([binary,*args,'-v',selected,'-b','1','-s','175','-f','source.txt','-w','speech.wav'],cwd=work,timeout=120,check_continue=bounded,environment=environment)
        bounded()
        try:
            with wave.open(str(output)) as audio:
                rate=audio.getframerate();channels=audio.getnchannels();width=audio.getsampwidth();count=audio.getnframes();raw=audio.readframes(count)
                if channels!=1 or width!=2 or rate<=0 or not 0<count/rate<=300 or len(raw)!=count*2:raise VideoEditingError('TTS_AUDIO_INVALID')
        except (wave.Error,OSError,EOFError) as exc:raise VideoEditingError('TTS_AUDIO_INVALID') from exc
        _run([ffmpeg,'-v','error','-nostdin','-n','-protocol_whitelist','file','-format_whitelist','wav','-i',str(output),'-map','0:a:0','-c:a','pcm_s16le','-f','s16le',str(pcm)],cwd=work,timeout=30,check_continue=bounded)
        if pcm.read_bytes()!=raw:raise VideoEditingError('TTS_FULL_DECODE_MISMATCH')
        samples=array.array('h');samples.frombytes(raw)
        if not samples or max(abs(value) for value in samples)==0:raise VideoEditingError('TTS_AUDIO_SILENT')
        data=output.read_bytes();check()
        if hashlib.sha256(Path(binary).read_bytes()).hexdigest()!=binary_hash:raise VideoEditingError('TTS_RUNTIME_CHANGED')
    report={'engine':'espeak_ng','engine_ownership':'third_party','engine_version':(re.search(r'\d+\.\d+(?:\.\d+)?',version).group(0) if re.search(r'\d+\.\d+(?:\.\d+)?',version) else 'unknown'),
            'engine_sha256':binary_hash,'language':language,'voice':selected,
            'synthesis_method':'formant_non_neural','synthetic':True,'voice_cloned':False,'external_network_used':False,
            'naturalness':'NOT_EVALUATED_EXPECT_MECHANICAL_VOICE','pronunciation_accuracy':'NOT_EVALUATED',
            'source':{'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'canonical_fact':False},
            'audio':{'duration_sec':count/rate,'sample_rate':rate,'channels':channels,'sample_width_bytes':width,
                     'decoded_samples_per_channel':count,'full_decode':'passed','full_pcm_comparison':'passed',
                     'pcm_sha256':hashlib.sha256(raw).hexdigest(),'sample_peak':max(abs(v) for v in samples)/32768},
            'audio_trimmed':False,'text_truncated':False,'published':False,
            'license':'GPL-3.0-or-later (external engine; not redistributed)',
            'references':['https://github.com/espeak-ng/espeak-ng','https://github.com/espeak-ng/espeak-ng/blob/master/docs/languages.md'],
            'outputs':{'speech.wav':{'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)}}}
    return {'files':{'speech.wav':data,'speech.json':json.dumps(report,ensure_ascii=False,indent=2).encode()},'report':report}
