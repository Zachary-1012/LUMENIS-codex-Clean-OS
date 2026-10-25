"""Actual local raster/vector/Office encoding on isolated original SavedWork."""
import base64
import copy
import hashlib
import io
import xml.etree.ElementTree as ET

import pytest
from PIL import Image

from tests.test_saved_document_workflow import workspace
from lumenis.shared.content_creation.audio_visuals import (
    validate_visual_document,visual_document_markdown,export_visual_document)
from lumenis.shared.content_creation.video_editing import VideoEditingError


def document():
    image = io.BytesIO();Image.new('RGB',(24,12),'blue').save(image,format='PNG');raw=image.getvalue()
    common = dict(x=0,y=0,width=100,height=70,rotation=0,opacity=1,visible=True,locked=False)
    return {'schema':'lumenis.visual-document/v1','canvas':{'width':320,'height':200,'background':'#ffffff'},
        'assets':[{'id':'photo','media_type':'image/png','sha256':hashlib.sha256(raw).hexdigest(),
                   'data_base64':base64.b64encode(raw).decode()}],
        'layers':[
            {**common,'id':'background','name':'Red block','kind':'rectangle','x':5,'y':5,
             'fill':'#ff0000','stroke':'#000000','stroke_width':0},
            {**common,'id':'title','name':'Editable title','kind':'text','x':125,'width':180,'height':90,
             'text':'OEVIRA\nVisual studio','font_size':20,'color':'#111111','align':'left','line_height':1.1},
            {**common,'id':'picture','name':'Original image','kind':'image','x':5,'y':105,
             'asset_id':'photo','fit':'contain'},
            {**common,'id':'ellipse','name':'Green circle','kind':'ellipse','x':200,'y':110,'width':60,'height':60,
             'fill':'#00ff00','stroke':'#111111','stroke_width':2},
        ]}


def save(ws,value,**extra):
    args = dict(title='Editable visual',markdown=visual_document_markdown(value),kind='report',
                payload={'visual_document':value},citations=[],request_id='visual-request-0001',
                actor=ws['actor'],scope=ws['scope'],work_id=None,previous_artifact_id=None)
    args.update(extra)
    resource=ws['work'].work_write_resource(**args)
    ws['gate'].grant_approval('data_export',resource=resource,granted_by='isolated visual encoding test')
    return ws['work'].save_work(**args)


def test_actual_raster_svg_and_editable_powerpoint():
    value=document();original=copy.deepcopy(value)
    png=export_visual_document(value,format='png')
    with Image.open(io.BytesIO(png)) as image:
        assert image.size==(320,200)
        assert image.getpixel((30,30))==(255,0,0,255)
        assert image.getpixel((30,135))==(0,0,255,255)
    svg=ET.fromstring(export_visual_document(value,format='svg'))
    assert len(svg.findall('{http://www.w3.org/2000/svg}g'))==4
    assert 'Visual studio' in ''.join(svg.itertext())
    assert export_visual_document(value,format='pdf').startswith(b'%PDF-')
    from pptx import Presentation
    deck=Presentation(io.BytesIO(export_visual_document(value,format='pptx')))
    assert len(deck.slides)==1 and len(deck.slides[0].shapes)==4
    text=deck.slides[0].shapes[1]
    assert text.text=='OEVIRA\nVisual studio'
    text.text='Revised in native object model'
    output=io.BytesIO();deck.save(output)
    assert Presentation(io.BytesIO(output.getvalue())).slides[0].shapes[1].text=='Revised in native object model'
    assert value==original


def test_save_revise_old_version_reopen_and_export(workspace):
    ws=workspace;value=document();first=save(ws,value);ref=first['artifact']['artifact_id']
    assert ws['work'].reopen_work(ref,actor=ws['actor'],scope=ws['scope'])['document']['payload']['visual_document']==value
    revision=dict(request_id='visual-revise-0002',expected_sha256=first['artifact']['sha256'],reason='Move and change title',
        edits=[{'pointer':'/payload/visual_document/layers/1/text','expected':'OEVIRA\nVisual studio','value':'User revision'},
               {'pointer':'/payload/visual_document/layers/0/x','expected':5,'value':18}])
    prepared=ws['work']._prepare_work_revision(ref,actor=ws['actor'],scope=ws['scope'],**revision)[1]
    second=save(ws,prepared['payload']['visual_document'],request_id='visual-revise-0002',work_id=first['document']['work_id'],
        previous_artifact_id=ref,expected_draft_digest=first['document']['draft_digest'])
    assert second['document']['version']==2
    cold=ws['work'].reopen_work(second['artifact']['artifact_id'],actor=ws['actor'],scope=ws['scope'])
    assert cold['document']['payload']['visual_document']['layers'][1]['text']=='User revision'
    assert ws['work'].reopen_work(ref,actor=ws['actor'],scope=ws['scope'])['document']['payload']['visual_document']==value
    for fmt in ['png','svg','pptx','pdf','json']:
        bound={'id':second['artifact']['artifact_id'],'sha256':second['artifact']['sha256'],'format':fmt}
        ws['gate'].grant_approval('data_export',resource='saved-work-export:v1:'+ws['work']._digest(bound),granted_by='isolated export')
        result=ws['work'].export_work(second['artifact']['artifact_id'],actor=ws['actor'],scope=ws['scope'],format=fmt)
        assert result['sha256']==hashlib.sha256(result['content']).hexdigest()
    assert save(ws,value)['replayed'] is True


def test_locked_object_and_original_raster_cannot_change_silently():
    old=document();old['layers'][2]['locked']=True;new=copy.deepcopy(old)
    new['layers'][2]['x']=40
    with pytest.raises(VideoEditingError,match='VISUAL_LAYER_LOCKED'):validate_visual_document(new,previous=old)
    new['layers'][2]['locked']=False
    validate_visual_document(new,previous=old)
    old['assets'][0]['data_base64']='PHN2ZyBvbmxvYWQ9ImFsZXJ0KDEpIi8+' # executable SVG is never a raster
    with pytest.raises(VideoEditingError,match='VISUAL_ASSET_INTEGRITY_FAILED'):validate_visual_document(old)


def test_hidden_layers_preserved_and_text_overflow_never_truncates():
    value=document();value['layers'][0]['visible']=False
    png=export_visual_document(value,format='png')
    with Image.open(io.BytesIO(png)) as image:assert image.getpixel((30,30))==(255,255,255,255)
    value['layers'][1]['height']=2
    with pytest.raises(VideoEditingError,match='VISUAL_TEXT_OVERFLOW_REQUIRES_EDIT'):export_visual_document(value,format='png')


def test_cancel_and_image_hash_failure_return_no_export():
    def cancelled():raise PermissionError('explicit cancellation')
    with pytest.raises(PermissionError,match='explicit cancellation'):
        export_visual_document(document(),format='png',check_cancel=cancelled)
    value=document();value['assets'][0]['sha256']='0'*64
    with pytest.raises(VideoEditingError,match='VISUAL_ASSET_INTEGRITY_FAILED'):export_visual_document(value,format='svg')
