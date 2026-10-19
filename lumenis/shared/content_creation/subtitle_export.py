"""Literal ASS sidecars; reference: https://aegisub.org/docs/latest/ass_tags/."""
from __future__ import annotations
import hashlib
import json
import math
import unicodedata
from PIL import ImageFont
from .video_editing import Timeline,VideoEditingError


def display_caption_text(overlay):
    text=overlay.text.replace('\r\n','\n')
    if any(unicodedata.category(c).startswith('C') and c!='\n' for c in text):
        raise VideoEditingError('SUBTITLE_TEXT_NOT_SUPPORTED')
    style=overlay.style
    if not style:return text
    lines=[]
    for original in text.split('\n'):
        line='';columns=0
        for char in original:
            mark=unicodedata.category(char).startswith('M')
            if columns==style.max_chars_per_line and not mark:
                lines.append(line);line='';columns=0
            line+=char;columns+=int(not mark)
        lines.append(line)
    if len(lines)>style.max_lines:raise VideoEditingError('CAPTION_STYLE_LINE_COUNT_EXCEEDED')
    return '\n'.join(lines)


def build_ass_files(timeline:Timeline):
    from .rendering import CAPTION_FONT,FRAME_RATE,FRAME_SIZES,_verify_caption_glyphs,_frame_at,subtitle_documents
    timeline.validate();subtitle_documents(timeline)  # Validate matching frame-quantized intervals.
    captions=sorted((item for item in timeline.overlays if item.kind=='caption'),key=lambda item:item.start_sec)
    if not captions:raise VideoEditingError('ASS_REQUIRES_CAPTIONS')
    width,height=FRAME_SIZES[timeline.format_ratio]
    texts=[display_caption_text(item) for item in captions]
    # ASS braces/backslashes are executable markup, never accept them as literal
    # text without a provably portable escaping rule. SRT/VTT remain available.
    if any(any(c in text for c in '{}\\') for text in texts):
        raise VideoEditingError('ASS_LITERAL_MARKUP_NOT_SUPPORTED')
    _verify_caption_glyphs('\n'.join(texts))
    family=ImageFont.truetype(str(CAPTION_FONT),size=24).getname()[0]
    if any(c in family for c in ',\n\r'):raise VideoEditingError('ASS_FONT_NAME_NOT_SUPPORTED')
    def color(value,opacity=1):
        rgb=value.lstrip('#');return f'&H{round((1-opacity)*255):02X}{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}'
    def timestamp(frame):
        cs=round(frame*100/FRAME_RATE);hours,cs=divmod(cs,360000);minutes,cs=divmod(cs,6000);seconds,cs=divmod(cs,100)
        return f'{hours}:{minutes:02}:{seconds:02}.{cs:02}'
    header=['[Script Info]','ScriptType: v4.00+',f'PlayResX: {width}',f'PlayResY: {height}','WrapStyle: 2','ScaledBorderAndShadow: yes','',
            '[V4+ Styles]','Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding']
    events=['','[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    for i,(item,text) in enumerate(zip(captions,texts)):
        style=item.style;size=style.font_size if style else max(16,width//36)
        fg=color(style.color if style else '#FFFFFF');bg=color(style.background_color if style else '#000000',style.background_opacity if style else .6)
        mx=math.ceil(width*style.safe_margin_ratio) if style else max(16,height//24)
        my=math.ceil(height*style.safe_margin_ratio) if style else max(16,height//24)
        alignment=8 if style and style.position=='top' else 2
        header.append(f'Style: Cue{i},{family},{size},{fg},{fg},{bg},{bg},0,0,0,0,100,100,0,0,3,8,0,{alignment},{mx},{mx},{my},1')
        start=math.ceil(round(item.start_sec*FRAME_RATE,6));end=min(math.ceil(round(item.end_sec*FRAME_RATE,6)),_frame_at(timeline.duration_sec))
        events.append(f'Dialogue: 0,{timestamp(start)},{timestamp(end)},Cue{i},,0,0,0,,',)
        events[-1]+=text.replace('\n',r'\N')
    data=('\n'.join(header+events)+'\n').encode('utf-8')
    report={'format':'ass','font_family':family,'font_sha256':hashlib.sha256(CAPTION_FONT.read_bytes()).hexdigest(),
            'font_embedded':False,'external_font_availability':'required_not_verified','cue_count':len(captions),
            'timing_quantization_seconds':.01,'pixel_identical_to_burned_output':False,'literal_markup_rejected':True}
    return {'files':{'captions.ass':data,'subtitles.json':json.dumps(report,ensure_ascii=False,sort_keys=True).encode()},'report':report}
