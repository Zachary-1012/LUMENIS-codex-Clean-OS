import pytest
from ai_browser_runtime import ActionVerifier, ExpectedState
@pytest.mark.parametrize('expected,actual',[
 (ExpectedState(status_code=200),{'loading':False}),
 (ExpectedState(status_code=200),{'loading':False,'status_code':None}),
 (ExpectedState(status_code=200),{'loading':False,'status_code':True}),
 (ExpectedState(input_value=('#a','')),{'loading':False,'elements':{}}),
 (ExpectedState(element_count_gte=('#a',0)),{'loading':False,'elements':{}}),
 (ExpectedState(element_count_gte=('#a',-1)),{'loading':False,'elements':{'#a':{'count':0}}}),
 (ExpectedState(),{}),
 (ExpectedState(),{'loading':None}),
 (ExpectedState(text_absent='error'),{'loading':False}),
 (ExpectedState(text_absent='error'),{'loading':False,'body_text':'ok','truncated_fields':['body_text']}),
 (ExpectedState(custom_check='purchase completed'),{'loading':False}),
])
def test_unknown_or_unperformed_check_cannot_pass(expected,actual):
 assert not ActionVerifier().verify(expected,actual).passed
@pytest.mark.parametrize('expected,actual',[
 (ExpectedState(status_code=200),{'loading':False,'status_code':200}),
 (ExpectedState(input_value=('#a','')),{'loading':False,'elements':{'#a':{'value':''}}}),
 (ExpectedState(element_count_gte=('#a',0)),{'loading':False,'elements':{'#a':{'count':0}}}),
 (ExpectedState(text_absent='error'),{'loading':False,'body_text':'ok'}),
])
def test_actual_zero_empty_and_observed_success_preserved(expected,actual):
 assert ActionVerifier().verify(expected,actual).passed

@pytest.mark.parametrize('actual',[{'loading':False,'elements':{}},{'loading':False,'elements':{'#x':{}}}])
def test_missing_element_empty_text_not_verified(actual):
 assert not ActionVerifier().verify(ExpectedState(element_text=('#x','')),actual).passed
@pytest.mark.parametrize('actual',[{'loading':False,'elements':{'#x':{'visible':'false'}}},{'loading':False,'elements':{'#x':{'visible':1}}}])
def test_unknown_visibility_not_verified(actual):
 assert not ActionVerifier().verify(ExpectedState(element_visible='#x'),actual).passed
