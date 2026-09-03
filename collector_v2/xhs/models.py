"""
小红书数据模型
"""
from dataclasses import dataclass, field
from typing import List, Optional
from ..base import RawNote, RawComment


@dataclass
class XHSNote(RawNote):
    """小红书笔记（扩展原始笔记模型）"""
    source_platform: str = 'xhs'
    note_type: str = 'normal'  # normal / video / image
    xsec_token: str = ''
    image_list: List[str] = field(default_factory=list)
    video_url: str = ''
    tag_list: List[str] = field(default_factory=list)
    location: str = ''
    ip_location: str = ''


@dataclass
class XHSComment(RawComment):
    """小红书评论"""
    ip_location: str = ''
    sub_comments: List['XHSComment'] = field(default_factory=list)
    like_users: List[str] = field(default_factory=list)
