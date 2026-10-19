from tests.test_bmp04_scoped_classification import setup,isolated_client,write

def test_foreign_legacy_rows_cannot_hide_current_classification(setup):
    cli,db,h,ids,eid=setup
    write(cli,h,ids[0],'brand_event','scope-limit-review')
    before=cli.get('/api/experience/screen/BMP-04',headers=h).get_json()['truth']
    assert before['dashboards'][0]['observed_events']==1
    import database
    with database.get_db() as con:
        con.executemany("INSERT INTO brand_propagation_events(event_id,title,category) VALUES(?, 'unrelated legacy', 'brand_event')", [(f'AAA-{i:04}',) for i in range(1001)])
    after=cli.get('/api/experience/screen/BMP-04',headers=h).get_json()['truth']
    assert after['dashboards'][0]['observed_events']==1

def test_copied_metadata_wrong_classification_id_rejected(setup):
    cli,db,h,ids,eid=setup
    write(cli,h,ids[0],'brand_event','duplicate-review')
    import database
    with database.get_db() as con:
        con.execute("INSERT INTO brand_propagation_events(event_id,title,category,metadata) SELECT 'copied-id',title,category,metadata FROM brand_propagation_events LIMIT 1")
    after=cli.get('/api/experience/screen/BMP-04',headers=h).get_json()['truth']
    assert after['dashboards'][0]['observed_events']==1
