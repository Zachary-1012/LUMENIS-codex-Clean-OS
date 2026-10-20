import sys,time,threading,json
from concurrent.futures import ThreadPoolExecutor
from tests.test_browser_extract import runtime, request, URL
from ai_browser_runtime import sanitize_sensitive
from lumenis.system.collector.runtime.browser_extract import BrowserExtractionError
print('AUTHORIZATION',sanitize_sensitive('Authorization: Bearer opaqueSecret123'))
o,c=runtime();o._browser_worker=ThreadPoolExecutor(max_workers=1); o._browser_worker.submit(time.sleep,.4)
t=time.monotonic();r=o.capture_command({'command':'preview','request_id':'queue-0001',**request(timeout_ms=100)})
print('QUEUE',round(time.monotonic()-t,3),'ok',r['ok']);o._browser_worker.shutdown()
o,c=runtime();o._human_control_token_digest='held';o._human_control_expires_at=time.time()+60
p={'command':'preview','request_id':'lease-0001',**request()}
try:o.capture_command(p)
except Exception as e:print('LEASE_INITIAL',type(e).__name__,getattr(e,'code',str(e)))
o._human_control_token_digest=None
try:print('LEASE_RETRY',o.capture_command(p))
except Exception as e:print('LEASE_RETRY',type(e).__name__,getattr(e,'code',str(e)))
o,c=runtime();o._record_evidence.side_effect=lambda **kw:(time.sleep(.15) or 7)
p={'command':'preview','request_id':'unknown-0001',**request(timeout_ms=100)}
try:o.capture_command(p)
except BrowserExtractionError as e:print('UNKNOWN_INITIAL',e.code,e.details)
entry=next(iter(o._capture_previews.values()));entry['expires']=time.monotonic()-1
try:o.capture_command(p)
except BrowserExtractionError as e:print('UNKNOWN_EXPIRED_REPLAY',e.code,e.details)
