"""Deterministic offline podcast artwork through the existing media owner."""
import hashlib,json
from .audio_visuals import _card,_copy_text,_source_unchanged,_check
from . import rendering
from .video_editing import MediaAsset,VideoEditingError


def build_podcast_cover_files(asset,*,title,subtitle,footer='离线节目封面',check_cancel=None):
    from shared_artifacts import validate_local_asset
    _check(check_cancel)
    if not isinstance(asset,MediaAsset) or asset.audio_stream_count!=1:
        raise VideoEditingError('PODCAST_COVER_SINGLE_AUDIO_SOURCE_REQUIRED')
    asset.validate();validate_local_asset(asset.path);_source_unchanged(asset,check_cancel)
    title=_copy_text(title,80);subtitle=_copy_text(subtitle,240);footer=_copy_text(footer,80)
    if not rendering.CAPTION_FONT.is_file():raise VideoEditingError('PODCAST_COVER_FONT_UNAVAILABLE')
    rendering._verify_caption_glyphs(title+subtitle+footer)
    font_hash=hashlib.sha256(rendering.CAPTION_FONT.read_bytes()).hexdigest()
    image,verification=_card(title=title,quote=subtitle,stamp=footer,width=3000,height=3000,
                            waveform=None,check_cancel=check_cancel,typography_scale=3)
    _source_unchanged(asset,check_cancel)
    if hashlib.sha256(rendering.CAPTION_FONT.read_bytes()).hexdigest()!=font_hash:
        raise VideoEditingError('PODCAST_COVER_FONT_CHANGED')
    _check(check_cancel)
    if len(image)>32*1024*1024:raise VideoEditingError('PODCAST_COVER_OUTPUT_LIMIT')
    report={'schema':'lumenis.podcast-cover/v1','state':'rendered_verified','design_method':'deterministic_literal_text_layout',
            'source_asset_id':asset.asset_id,'source_sha256':asset.sha256,'source_kind':'final_rendered_programme',
            'copy':{'title':title,'subtitle':subtitle,'footer':footer},'copy_semantics':'user_supplied_not_independently_verified',
            'font_sha256':font_hash,'font_embedded':False,'verification':verification,
            'platform_acceptance':'NOT_VERIFIED','brand_or_aesthetic_acceptance':'NOT_VERIFIED','published':False,
            'outputs':{'podcast-cover.png':{'sha256':hashlib.sha256(image).hexdigest(),'size_bytes':len(image)}}}
    return {'files':{'podcast-cover.png':image,'podcast-cover.json':json.dumps(report,ensure_ascii=False,indent=2).encode()},'report':report}
