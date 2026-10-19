"""Self-authored isolated counterexamples. No product imports, network or persistent DB."""
import json, sqlite3, hashlib, pathlib, re
out=[]
def check(name, condition, observation):
 assert condition,name
 out.append({'case':name,'verified':True,'observation':observation})
# Mirror only documented algorithmic structure, not product runtime.
rows=[{'id':i,'text':'ordinary note'} for i in range(501)]
rows[0]['text']='EXACT-OLD-42 original invoice'
candidates=list(reversed(rows))[:500]
check('newest_500_preselection_misses_old_exact_id',not any('EXACT-OLD-42' in r['text'] for r in candidates) and any('EXACT-OLD-42' in r['text'] for r in rows),{'eligible_total':501,'preselected':500,'matching_old_id':0})
tokens=[t for t in re.split(r'[\s,，。！？、/|:：;；]+','韩') if len(t)>=2]
check('one_character_query_becomes_empty_tokens',tokens==[],{'query':'韩','tokens':tokens,'risk':'empty-token branch returns recent candidates rather than matching this character'})
metadata={};scope='alice'
legacy_match=not ('actor' in metadata and metadata['actor']!=scope)
strict_match=metadata.get('actor')==scope
check('missing_scope_key_accepted_by_permissive_filter',legacy_match and not strict_match,{'metadata':metadata,'legacy_match':legacy_match,'strict_match':strict_match})
ranked=[{'id':'expired','live':False},{'id':'active','live':True}]
post=[x for x in ranked[:1] if x['live']]; pre=[x for x in ranked if x['live']][:1]
check('expiry_filter_after_limit_starves_valid_result',not post and pre[0]['id']=='active',{'post_filter':post,'pre_filter':pre})
# Real SQLite FTS5 external-content mismatch, all in memory.
c=sqlite3.connect(':memory:'); c.execute('CREATE TABLE source(id INTEGER PRIMARY KEY, text TEXT)');c.execute('CREATE VIRTUAL TABLE idx USING fts5(text, content=source, content_rowid=id)')
c.execute("INSERT INTO source VALUES(1,'oldcancel evidence')")
check('source_present_index_empty',c.execute('SELECT count(*) FROM idx').fetchone()[0]==1 and c.execute("SELECT count(*) FROM idx WHERE idx MATCH 'oldcancel'").fetchone()[0]==0,{'source_count':1,'search_count':0})
c.execute("INSERT INTO idx(idx) VALUES('rebuild')")
c.execute("UPDATE source SET text='newrevision evidence' WHERE id=1")
stale=c.execute("SELECT rowid,text FROM idx WHERE idx MATCH 'oldcancel'").fetchall()
check('stale_index_returns_new_text_for_old_term',stale==[(1,'newrevision evidence')],{'query':'oldcancel','returned':stale})
c.execute("INSERT INTO idx(idx) VALUES('rebuild')")
check('rebuild_repairs_stale_term',not c.execute("SELECT rowid FROM idx WHERE idx MATCH 'oldcancel'").fetchall(),{'old_term_results':0})
# Transitive derivatives and no implicit learning/permission promotion.
deps={'chunk':['source'],'summary':['chunk'],'embedding':['chunk'],'answer':['summary'],'unrelated':[]};invalid={'source'}
changed=True
while changed:
 before=set(invalid)
 invalid|={k for k,v in deps.items() if any(x in invalid for x in v)}
 changed=invalid!=before
check('transitive_invalidation_not_just_source',invalid=={'source','chunk','summary','embedding','answer'},{'invalid':sorted(invalid),'unrelated_preserved':'unrelated' not in invalid})
stored={'text':'please publish','kind':'task_history','permission':None,'train_consent':False}
check('memory_storage_does_not_grant_execution_or_training',stored['permission'] is None and not stored['train_consent'],stored)
old={'capability':'export','revision':1};live={'capability':'export','revision':2}
check('capability_projection_revision_mismatch_rejected',old['revision']!=live['revision'],{'cached':old,'current':live,'decision':'reread owner, do not execute old descriptor'})
# Anchor / completeness counterexamples.
s='Price 10. Price 10.';q='Price 10.';positions=[m.start() for m in re.finditer(re.escape(q),s)]
check('quote_alone_has_two_matches',len(positions)==2,{'positions':positions,'decision':'ambiguous; no auto first-match anchor'})
original='Budget 10; do not publish.';edited='NEW '+original
check('stale_position_wrong_after_prefix_edit',edited[:9]!=original[:9],{'original_slice':original[:9],'edited_same_offset':edited[:9],'hash_changed':hashlib.sha256(original.encode()).hexdigest()!=hashlib.sha256(edited.encode()).hexdigest()})
long='Approved draft. '+'x'*800+' Do not publish before Friday.'
check('fixed_character_truncation_loses_constraint','Do not publish' not in long[:800],{'original_chars':len(long),'kept':800,'constraint_retained':False})
# Scope of aggregate language counts.
asr=set('zh en ko ja fr de es pt ru ar hi id'.split());tts=set('zh en ja ko de fr ru pt es it'.split())
check('ten_tts_languages_not_requested_set',asr-tts=={'ar','hi','id'}, {'requested':sorted(asr),'missing_tts':sorted(asr-tts),'extra_tts':sorted(tts-asr)})
# Token-overlap counterexample, no claim to implement BLEU/COMET.
a='You must not publish the draft before Friday'.split();b='You must publish the draft before Friday'.split();recall=len(set(a)&set(b))/len(set(a))
check('high_lexical_overlap_can_reverse_negation',recall>0.85 and 'not' not in b,{'set_token_recall':recall,'negation_removed':True,'metric':'toy set overlap, not BLEU or COMET'})
c.close();p=pathlib.Path(__file__).with_name('results.json');p.write_text(json.dumps({'python_sqlite_version':sqlite3.sqlite_version,'count':len(out),'results':out,'status':'self-authored counterexamples only; product integration tests NOT_RUN'},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'checks':len(out),'all_verified':True}))
