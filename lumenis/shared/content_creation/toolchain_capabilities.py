"""Read-only observations of this machine, never a cross-platform promise."""
import hashlib,re,shutil,subprocess,platform
from pathlib import Path


def _available_filter_names(output):
    """Parse FFmpeg's two- or three-character filter flag column."""
    names = set()
    for line in (output or "").splitlines():
        match = re.match(r"^\s*[TSC.]{2,3}\s+([A-Za-z0-9_]+)\s", line)
        if match:
            names.add(match.group(1))
    return names


def inspect_media_toolchain():
    from shared_artifacts import _ffmpeg_path
    from .video_editing import _ffprobe_path
    from .rendering import CAPTION_FONT,_verify_caption_glyphs
    def command(binary,*args,environment=None):
        if not binary:return None
        try:
            result=subprocess.run([binary,*args],capture_output=True,text=True,timeout=10,check=False,shell=False,env=environment)
            return (result.stdout+result.stderr)[:2000000] if result.returncode==0 else None
        except (OSError,subprocess.SubprocessError):return None
    ffmpeg=_ffmpeg_path();probe=_ffprobe_path();filters=command(ffmpeg,'-hide_banner','-filters')
    names = _available_filter_names(filters)
    needed={'flite':'local_english_synthetic_speech','afftdn':'explicit_fft_noise_reduction','ass':'ASS_subtitle_playback','drawtext':'burned_captions','loudnorm':'measured_loudness_mastering','sidechaincompress':'voiceover_music_ducking'}
    states={name:{'available':name in names,'capability':capability} for name,capability in needed.items()}
    font={'available':CAPTION_FONT.is_file(),'filename':CAPTION_FONT.name,'path':str(CAPTION_FONT),'glyph_probe':'序境 中文 English 한국어','glyphs_available':False}
    if font['available']:
        font['sha256']=hashlib.sha256(CAPTION_FONT.read_bytes()).hexdigest()
        try:_verify_caption_glyphs(font['glyph_probe']);font['glyphs_available']=True
        except ValueError:pass
    office=shutil.which('libreoffice') or shutil.which('soffice')
    espeak={'available':False,'supported_requested_languages':[],'synthesis_method':'formant_non_neural','naturalness':'NOT_EVALUATED'}
    try:
        from .offline_formant_speech import _runtime
        binary,args,environment=_runtime()
        voices=command(binary,*args,'--voices',environment=environment)
        observed={line.split()[1] for line in (voices or '').splitlines()[1:] if len(line.split())>2}
        espeak.update(available=bool(voices),path=binary,supported_requested_languages=[lang for lang in ('cmn','ko','en-us') if lang in observed])
    except ValueError:pass
    from .speech_transcription import speech_runtime_status
    return {'speech_runtime':speech_runtime_status(),'espeak_ng':espeak,'platform':platform.system(),'ffmpeg':{'available':bool(filters),'path':ffmpeg,'version':(command(ffmpeg,'-version') or '').splitlines()[:1],
              'filters':states},'ffprobe':{'available':bool(command(probe,'-version')),'path':probe},'caption_font':font,
            'libreoffice':{'available':bool(office),'path':office,'version':(command(office,'--version') or '').splitlines()[:1]},
            'cross_platform_verified':False,'automatic_install':False,'binaries_redistributed':False,
            'missing_capabilities':[value['capability'] for value in states.values() if not value['available']],
            'installation_guidance':'Install an official FFmpeg build with the listed filters, ffprobe, a licensed CJK font covering requested glyphs, and LibreOffice for office/PDF conversion. Windows/macOS require their own readback; no binary or font is included.'}
