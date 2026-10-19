from tests.test_independent_growth_real_app import real_app,headers,BASE,counts
from tests.test_saved_document_workflow import workspace

def test_nine_dimension_summary_is_complete_before_paging_and_actor_bound(real_app):
    ws=real_app;api=ws['api'];created=[]
    for actor,dimension in [(201,'business')]*4+[(201,'technology')]*2+[(202,'business')]*7:
        response=api.post(BASE+'/start',headers=headers(actor),json={'defer':True,'research':{'dimension':dimension}})
        assert response.status_code==202,response.get_json()
        if actor==201:created.append(response.get_json()['task'])
    domain_headers={'Authorization':headers(201)['Authorization'],'X-Domain-Id':'CTH','X-Product-Id':'CTH','X-Lumenis-Context-Mode':'GLOBAL_ALL'}
    response=api.post(BASE+'/start',headers=domain_headers,json={'defer':True,'research':{'dimension':'business'}})
    assert response.status_code==202,response.get_json()
    assert api.get(BASE+'/tasks',headers=domain_headers).get_json()['result']['summary']['total']==1
    before=counts(ws)
    first=api.get(BASE+'/tasks',headers=headers(201),query_string={'limit':1})
    assert first.status_code==200,first.get_json()
    value=first.get_json()['result'];summary=value['summary']
    assert len(value['items'])==1 and value['total']==6 and summary['total']==6
    assert len(summary['dimensions'])==9
    rows={row['key']:row for row in summary['dimensions']}
    assert rows['business']['states']['pending']==4
    assert rows['technology']['states']['pending']==2
    assert sum(row['task_count'] for row in rows.values())==6
    page=api.get(BASE+'/tasks',headers=headers(201),query_string={'limit':1,'dimension':'technology'}).get_json()['result']
    assert page['total']==2 and page['summary']==summary
    foreign=api.get(BASE+'/tasks',headers=headers(202),query_string={'limit':1}).get_json()['result']
    assert foreign['summary']['total']==7
    assert counts(ws)==before
    task=created[0]
    cancelled=api.post(BASE+'/tasks/'+task['task_id']+'/cancel',headers=headers(201),json={'expected_revision':task['expected_revision']})
    assert cancelled.status_code==200,cancelled.get_json()
    fresh=api.get(BASE+'/tasks',headers=headers(201),query_string={'limit':1}).get_json()['result']['summary']
    rows={row['key']:row for row in fresh['dimensions']}
    assert fresh['total']==6 and rows['business']['states']['pending']==3 and rows['business']['states']['cancelled']==1
    with ws['repo'].transaction() as con:con.execute("UPDATE v4_users SET status='inactive' WHERE id=201")
    assert api.get(BASE+'/tasks',headers=headers(201)).status_code!=200
