import threading,types
import pytest
from lumenis.system.collector.guard import rate_limiter as m
@pytest.fixture
def clock(monkeypatch):
 c=types.SimpleNamespace(wall=1000.,mono=1000.)
 monkeypatch.setattr(m,'time',types.SimpleNamespace(time=lambda:c.wall,monotonic=lambda:c.mono,sleep=lambda _:None));return c

def advance(c,seconds):c.wall+=seconds;c.mono+=seconds

def test_jitter_never_shortens_retry_after(clock,monkeypatch):
 monkeypatch.setattr(m.random,'uniform',lambda a,b:.7);r=m.AdaptiveRateLimiter(base_interval=10,fail_threshold=1,cooldown_seconds=10);r.on_failure(retry_after=120)
 waits=[];r.wait_slot(sleep=lambda s:(waits.append(s),advance(clock,s)));assert waits[0]>=120

def test_retry_after_before_threshold_and_success_is_still_floor(clock):
 r=m.AdaptiveRateLimiter(base_interval=10,fail_threshold=5,jitter=False);r.on_failure(retry_after=120);r.on_success();assert not r.can_run();assert r.remaining_cooldown()==120

def test_delayed_concurrent_wake_is_actually_spaced(clock):
 r=m.AdaptiveRateLimiter(base_interval=10,jitter=False);barrier=threading.Barrier(2);lock=threading.Lock();returns=[];waits=[];tls=threading.local();first_return=threading.Event()
 def sleeper(seconds):
  with lock:waits.append(seconds)
  if not getattr(tls,'slept',False):
   tls.slept=True;barrier.wait(timeout=3)
   with lock:clock.mono=clock.wall=1030.
   barrier.wait(timeout=3)
  else:
   assert first_return.wait(timeout=3)
   with lock:advance(clock,seconds)
 def worker():
  r.wait_slot(sleep=sleeper)
  with lock:returns.append(clock.mono)
  first_return.set()
 threads=[threading.Thread(target=worker) for _ in range(2)]
 for t in threads:t.start()
 for t in threads:t.join(timeout=4)
 assert len(returns)==2 and max(returns)-min(returns)>=10
 assert len(waits)>=3

def test_cancelled_reservation_not_reused_early(clock):
 r=m.AdaptiveRateLimiter(base_interval=10,jitter=False);flag=[False]
 def sleep(s):advance(clock,s);flag[0]=True
 with pytest.raises(InterruptedError):r.wait_slot(sleep=sleep,cancelled=lambda:flag[0])
 flag[0]=False;r.wait_slot(sleep=lambda s:advance(clock,s));assert clock.mono>=1020

def test_sibling_success_cannot_clear_local_cooldown(clock):
 r=m.AdaptiveRateLimiter(fail_threshold=1,cooldown_seconds=600);r.on_failure();r.on_success();assert r.remaining_cooldown()==600 and not r.can_run()

def test_forward_wall_jump_cannot_expire_force_pause(clock):
 r=m.AdaptiveRateLimiter();r.force_pause(cooldown_seconds=600);clock.wall=100000.;assert r.remaining_cooldown()==600 and not r.can_run()

def test_backward_wall_jump_does_not_extend_elapsed_server_delay(clock):
 r=m.AdaptiveRateLimiter(fail_threshold=5);r.on_failure(retry_after=120);clock.wall=0.;clock.mono=1120.;assert r.can_run()

def test_new_cooldown_during_sleep_is_respected(clock):
 r=m.AdaptiveRateLimiter(base_interval=10,jitter=False);calls=[]
 def sleep(s):
  calls.append(s);advance(clock,s)
  if len(calls)==1:r.on_failure(retry_after=60)
 r.wait_slot(sleep=sleep);assert clock.mono>=1070 and len(calls)==2

def test_owner_instances_are_independent(clock):
 a=m.AdaptiveRateLimiter(base_interval=10,jitter=False);b=m.AdaptiveRateLimiter(base_interval=10,jitter=False)
 a.on_failure(retry_after=120);assert not a.can_run() and b.can_run()

def test_long_failure_burst_cannot_overflow_backoff(clock):
 r=m.AdaptiveRateLimiter(fail_threshold=1,cooldown_seconds=600)
 for _ in range(1100):r.on_failure();r.on_success()
 assert r.remaining_cooldown()==1800 and not r.can_run()
