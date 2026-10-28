"""Real offline podcast Plan/Timeline binding and immutable-parent regressions."""
import zipfile
from dataclasses import replace
import pytest
import shared_artifacts as a
from podcast.intelligence.episode_runtime import PodcastPlan,PodcastSegment
from lumenis.shared.content_creation.video_editing import AudioMix
from tests.test_content_project_storage import media_store,approve,import_source,ACTOR,SCOPE,rows

def prepare(store,separate=False):
    approve(store);sid=import_source(store)['artifact']['artifact_id']
    return sid

def plan_for(asset):
    return PodcastPlan('Actual local binding','Synthetic audible test','en',tuple(PodcastSegment(segment_id=f's{i}',media_asset_id=asset.asset_id,source_in=i*.2,source_out=(i+1)*.2,original_text=f'original {i}',corrected_text=f'corrected {i}',speaker=f'Speaker {i}',chapter_title=f'chapter {i}') for i in range(2)))

def stage(tl,plan,sid,**kw):
    return a.stage_timeline_artifact(tl,actor=ACTOR,**SCOPE,source_execution_id='podcast-binding-real',output_kind='audio',source_artifact_refs=[sid],delivery_options={'audio_formats':['mp3'],'podcast_plan':plan.to_dict()},**kw)

@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('role',['bgm','sfx'])
def test_real_auxiliary_render_seven_members_parent_and_reopen(media_store,separate,role):
    sid=prepare(media_store)
    with a.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as src:
        asset=src[0]['asset'];plan=plan_for(asset);tl=plan.build_timeline((asset,),separate_speakers=separate)
        parent=stage(tl,plan,sid);aid=parent['artifact']['artifact_id'];before=a.authorized_project_media(aid,actor=ACTOR,**SCOPE)['data']
        revised=tl.add_audio_track('ambience',audio_role=role).add_clip(asset.asset_id,track_id='ambience',audio_role=role,source_out=.4,purpose='permitted bed',audio_stream_index=0)
        clip=revised.tracks[-1].clips[0];revised=revised.set_audio_mix(clip.clip_id,AudioMix(volume=.15))
        child=stage(revised,plan,sid,previous_artifact_id=aid);bid=child['artifact']['artifact_id']
        opened=a.read_content_project(bid,actor=ACTOR,**SCOPE)
        assert opened['project']['parent_artifact_id']==aid
        assert opened['project']['timeline']==revised.to_dict()
        assert a.authorized_project_media(aid,actor=ACTOR,**SCOPE)['data']==before
        assert a.authorized_project_media(bid,actor=ACTOR,**SCOPE)['data']!=before
        with zipfile.ZipFile(media_store['root']/f'{bid}.zip') as z:
            assert set(plan.editable_documents())<=set(z.namelist())
            for name,text in plan.editable_documents().items(): assert z.read(name).decode()==text
        assert child['render']['delivery_reports']['mp3']['decode_all_frames']=='passed'

@pytest.mark.parametrize('change',['purpose','lane','order','source_range','extra_voice'])
def test_real_plan_binding_mismatch_preserves_parent(media_store,change):
    sid=prepare(media_store)
    with a.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as src:
        asset=src[0]['asset'];plan=plan_for(asset);tl=plan.build_timeline((asset,),separate_speakers=True)
        parent=stage(tl,plan,sid);aid=parent['artifact']['artifact_id'];before=a.read_content_project(aid,actor=ACTOR,**SCOPE);n=len(rows(media_store))
        tracks=list(tl.tracks);idx=next(i for i,t in enumerate(tracks) if t.clips);track=tracks[idx];clip=track.clips[0]
        if change=='purpose': tracks[idx]=replace(track,clips=(replace(clip,purpose='podcast-segment:foreign'),))
        elif change=='lane':
            # Swap whole speaker lanes while keeping each clip's track identifier valid.
            j=next(i for i,t in enumerate(tracks) if t.clips and i!=idx);other=tracks[j]
            tracks[idx]=replace(track,clips=tuple(replace(c,track_id=track.track_id) for c in other.clips));tracks[j]=replace(other,clips=tuple(replace(c,track_id=other.track_id) for c in track.clips))
        elif change=='order': tracks[idx]=replace(track,clips=(replace(clip,timeline_start=.2),))
        elif change=='source_range': tracks[idx]=replace(track,clips=(replace(clip,source_in=.01),))
        if change=='extra_voice': bad=tl.add_audio_track('extra',audio_role='voiceover').add_clip(asset.asset_id,track_id='extra',audio_role='voiceover',source_out=.1,audio_stream_index=0)
        else: bad=replace(tl,tracks=tuple(tracks),version=tl.version+1)
        with pytest.raises(a.LocalArtifactError,match='PODCAST_PLAN_TIMELINE_MISMATCH'): stage(bad,plan,sid,previous_artifact_id=aid)
        assert len(rows(media_store))==n
        assert a.read_content_project(aid,actor=ACTOR,**SCOPE)==before

@pytest.mark.parametrize('silence',['muted_track','zero_clip_gain','solo_music'])
def test_podcast_text_delivery_rejects_silenced_dialogue_before_render(media_store,monkeypatch,silence):
    sid=prepare(media_store)
    with a.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as src:
        asset=src[0]['asset'];plan=plan_for(asset);tl=plan.build_timeline((asset,),separate_speakers=True)
        tracks=list(tl.tracks)
        voice_index=next(i for i,item in enumerate(tracks) if item.kind=='voiceover' and item.clips)
        voice=tracks[voice_index]
        if silence=='muted_track':
            tracks[voice_index]=replace(voice,muted=True)
        elif silence=='zero_clip_gain':
            tracks[voice_index]=replace(voice,clips=(replace(voice.clips[0],audio_mix=AudioMix(volume=0)),*voice.clips[1:]))
        else:
            music=replace(tracks[0],track_id='music',kind='bgm',clips=(),solo=True)
            music=replace(music,clips=(replace(voice.clips[0],clip_id='music-clip',track_id='music',
                purpose='permitted music bed',audio_role='bgm'),))
            tracks.append(music)
        bad=replace(tl,tracks=tuple(tracks),version=tl.version+1)
        calls=[]
        monkeypatch.setattr('lumenis.shared.content_creation.rendering.render_timeline',
            lambda *args,**kwargs:calls.append('render'))
        count_before=len(rows(media_store))
        with pytest.raises(a.LocalArtifactError,match='PODCAST_PLAN_DIALOGUE_NOT_AUDIBLE'):
            stage(bad,plan,sid)
        assert calls==[]
        assert len(rows(media_store))==count_before

@pytest.mark.parametrize('denial',['wrong_actor','unknown_source_ref','revoked_account'])
def test_real_auxiliary_does_not_bypass_source_or_actor_permissions(media_store,denial):
    sid=prepare(media_store)
    with a.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as src:
        asset=src[0]['asset'];plan=plan_for(asset);tl=plan.build_timeline((asset,))
        parent=stage(tl,plan,sid);aid=parent['artifact']['artifact_id'];prior=a.authorized_project_media(aid,actor=ACTOR,**SCOPE)['data'];n=len(rows(media_store))
        revised=tl.add_audio_track('music',audio_role='bgm').add_clip(asset.asset_id,track_id='music',audio_role='bgm',source_out=.4,audio_stream_index=0)
        if denial=='revoked_account':
            with media_store['repository'].connect() as con: con.execute("UPDATE v4_users SET status='inactive' WHERE id=1")
        with pytest.raises(a.LocalArtifactError):
            a.stage_timeline_artifact(revised,actor={'id':2,'role':'admin'} if denial=='wrong_actor' else ACTOR,**SCOPE,source_execution_id='denial-'+denial,output_kind='audio',source_artifact_refs=['ART-'+'f'*16] if denial=='unknown_source_ref' else [sid],previous_artifact_id=aid,delivery_options={'audio_formats':['mp3'],'podcast_plan':plan.to_dict()})
        if denial=='revoked_account':
            with media_store['repository'].connect() as con: con.execute("UPDATE v4_users SET status='active' WHERE id=1")
        assert len(rows(media_store))==n
        assert a.authorized_project_media(aid,actor=ACTOR,**SCOPE)['data']==prior
