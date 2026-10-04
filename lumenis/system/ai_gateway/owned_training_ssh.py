"""SSH adapter for the existing owned trainer and Artifact byte owner.

Private Core session/signing state stays with the caller. No network listener,
provider, queue, schema or implicit credentials are created by this adapter.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import threading
import time


class RemoteTrainingError(RuntimeError):
    pass


def remote_path(value: str) -> str:
    if (type(value) is not str or not value.startswith('/') or value.startswith('//')
            or '\\' in value or any(ord(c) < 32 for c in value)
            or '..' in PurePosixPath(value).parts):
        raise RemoteTrainingError('REMOTE_PATH_INVALID')
    return str(PurePosixPath(value))


def relative_path(value: str) -> str:
    if (type(value) is not str or not value or '\\' in value or ':' in value
            or any(ord(c) < 32 for c in value)
            or PurePosixPath(value).is_absolute() or any(p in {'.', '..'} for p in value.split('/'))):
        raise RemoteTrainingError('CHECKPOINT_RELATIVE_PATH_INVALID')
    return value


def regular_local(path: Path):
    info = path.lstat()
    if (not path.is_absolute() or not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or getattr(info, 'st_file_attributes', 0) & 0x400 or info.st_nlink != 1):
        raise RemoteTrainingError('LOCAL_SSH_CONFIGURATION_INVALID')


@dataclass(frozen=True)
class SSHTrainingEndpoint:
    ssh_executable: Path
    host: str
    port: int
    user: str
    identity_file: Path
    known_hosts: Path
    remote_python: str
    source_root: str
    source_pins: dict[str, str]

    def __post_init__(self):
        if (type(self.host) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', self.host)
                or type(self.port) is not int or not 1 <= self.port <= 65535
                or type(self.user) is not str or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,63}', self.user)):
            raise RemoteTrainingError('SSH_ENDPOINT_INVALID')
        for path in (self.ssh_executable, self.identity_file, self.known_hosts):
            regular_local(path)
        remote_path(self.remote_python)
        remote_path(self.source_root)
        if not self.source_pins or type(self.source_pins) is not dict:
            raise RemoteTrainingError('REMOTE_SOURCE_PINS_REQUIRED')
        for path, digest in self.source_pins.items():
            relative_path(path)
            if type(digest) is not str or re.fullmatch(r'[0-9a-f]{64}', digest) is None:
                raise RemoteTrainingError('REMOTE_SOURCE_PINS_INVALID')

    def argv(self, command: str) -> list[str]:
        return [str(self.ssh_executable), '-T', '-a', '-F', 'none', '-p', str(self.port),
                '-i', str(self.identity_file), '-o', 'IdentitiesOnly=yes',
                '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                '-o', 'UserKnownHostsFile=' + str(self.known_hosts),
                '-o', 'GlobalKnownHostsFile=none', '-o', 'ClearAllForwardings=yes',
                '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=5',
                '-o', 'ServerAliveCountMax=2', self.user + '@' + self.host, command]


# Independent OS observation over the authenticated connection. A worker's
# hello dictionary is compared with this observation; it is not an authority.
_INSPECT = r'''
import hashlib,json,os,stat,sys,time
from pathlib import Path
b=json.loads(sys.stdin.buffer.readline())
pid=b['pid']; assert type(pid) is int and pid>1
root=Path(b['source_root']); assert root.is_absolute() and not root.is_symlink()
proc=Path('/proc')/str(pid)
text=(proc/'stat').read_text(); tail=text[text.rfind(')')+2:].split()
assert tail[0]!='Z'
boot=next(int(line.split()[1]) for line in Path('/proc/stat').read_text().splitlines() if line.startswith('btime '))
created=boot+int(tail[19])/os.sysconf('SC_CLK_TCK')
cwd=Path(os.readlink(proc/'cwd')); assert cwd.resolve()==root.resolve()
pins={}
for name,wanted in b['source_pins'].items():
 p=root/name; s=p.lstat(); assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_nlink==1
 actual=hashlib.sha256(p.read_bytes()).hexdigest(); assert actual==wanted; pins[name]=actual
value={'pid':pid,'created_at':created,'parent_pid':int(tail[1]),'process_group':int(tail[2]),
 'session_id':int(tail[3]),'proc_start_ticks':int(tail[19]),
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'source_root':str(cwd),'source_pins':pins,'state':'LIVE'}
print(json.dumps(value,separators=(',',':')),flush=True)
'''


_READ_FILE = r'''
import hashlib,json,os,stat,sys
from pathlib import Path
b=json.loads(sys.stdin.buffer.readline()); root=Path(b['root']); p=root/b['path']
assert root.is_absolute() and not root.is_symlink()
current=root
for part in Path(b['path']).parts:
 current=current/part; info=current.lstat(); assert not stat.S_ISLNK(info.st_mode)
assert p.resolve().is_relative_to(root.resolve())
fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
try:
 before=os.fstat(fd); assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size==b['bytes']
 digest=hashlib.sha256(); count=0
 while True:
  block=os.read(fd,1024*1024)
  if not block:break
  count+=len(block); assert count<=b['bytes']; digest.update(block);sys.stdout.buffer.write(block)
 sys.stdout.buffer.flush(); after=os.fstat(fd)
 assert count==b['bytes'] and digest.hexdigest()==b['sha256']
 assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
finally:os.close(fd)
'''


_WRITE_FILE = r'''
import hashlib,json,os,stat,sys
from pathlib import Path
b=json.loads(sys.stdin.buffer.readline()); root=Path(b['root']); p=root/b['path']
assert root.is_absolute()
root.mkdir(mode=0o700,parents=True,exist_ok=True); assert not root.is_symlink()
current=root
for part in Path(b['path']).parts[:-1]:
 current=current/part; current.mkdir(mode=0o700,exist_ok=True)
 assert stat.S_ISDIR(current.lstat().st_mode) and not current.is_symlink()
assert p.parent.resolve().is_relative_to(root.resolve())
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
try:
 digest=hashlib.sha256(); count=0
 while count<b['bytes']:
  block=sys.stdin.buffer.read(min(1024*1024,b['bytes']-count)); assert block
  digest.update(block); count+=len(block)
  view=memoryview(block)
  while view:view=view[os.write(fd,view):]
 assert not sys.stdin.buffer.read(1)
 assert count==b['bytes'] and digest.hexdigest()==b['sha256'];os.fsync(fd)
finally:os.close(fd)
assert hashlib.sha256(p.read_bytes()).hexdigest()==b['sha256']
print(json.dumps({'path':b['path'],'size_bytes':count,'sha256':digest.hexdigest()}))
'''

_ALLOCATE = r'''
import json,os,stat,sys
from pathlib import Path
b=json.loads(sys.stdin.buffer.readline()); root=Path(b['remote_root'])
assert root.is_absolute() and not root.exists()
for parent in root.parents:
 assert parent.is_dir() and not parent.is_symlink()
root.mkdir(mode=0o700,exist_ok=False)
assert stat.S_IMODE(root.stat().st_mode)==0o700 and not list(root.iterdir())
print(json.dumps({'remote_root':str(root),'empty':True}))
'''

_VERIFY_INPUTS = r'''
import hashlib,json,stat,sys
from pathlib import Path
b=json.loads(sys.stdin.buffer.readline()); paths=b['paths']; groups=b['files']
output=Path(paths['output_dir']); assert not output.exists() and not output.is_symlink()
for parent in output.parents:assert parent.is_dir() and not parent.is_symlink()
for key,entries in groups.items():
 p=Path(paths[key]); base=p if key=='model_snapshot_dir' else p.parent
 for parent in [base,*base.parents]:assert parent.is_dir() and not parent.is_symlink()
 expected=set()
 for e in entries:
  file=base/e['path']; expected.add(file)
  current=base
  for part in Path(e['path']).parts:
   current=current/part; assert not current.is_symlink()
  s=file.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_size==e['size_bytes']
  digest=hashlib.sha256()
  with file.open('rb') as f:
   before=f.stat() if hasattr(f,'stat') else s
   while True:
    block=f.read(1024*1024)
    if not block:break
    digest.update(block)
  after=file.lstat();assert digest.hexdigest()==e['sha256']
  assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
 if key=='model_snapshot_dir':
  actual=set()
  for file in base.rglob('*'):
   assert not file.is_symlink()
   if file.is_file():actual.add(file)
  assert actual==expected
 else:assert expected=={p}
 assert output!=p and not output.is_relative_to(p)
print(json.dumps({'paths':paths,'files':groups}))
'''


_STOP = r'''
import hashlib,json,os,signal,sys,time
from pathlib import Path
b=json.loads(sys.stdin.buffer.readline()); e=b['peer']; pid=e['pid']; group=e['process_group']
assert pid>1 and group==pid
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==e['boot_id']
def members():
 result=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   text=(p/'stat').read_text(); tail=text[text.rfind(')')+2:].split()
   if int(tail[2])==group and tail[0]!='Z':result.append(int(p.name))
  except (FileNotFoundError,ProcessLookupError):pass
 return result
def current():
 try:
  text=(Path('/proc')/str(pid)/'stat').read_text(); tail=text[text.rfind(')')+2:].split()
 except FileNotFoundError:return None
 boot=next(int(line.split()[1]) for line in Path('/proc/stat').read_text().splitlines() if line.startswith('btime '))
 created=boot+int(tail[19])/os.sysconf('SC_CLK_TCK')
 assert abs(created-e['created_at'])<0.001 and int(tail[2])==group
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==e['boot_id']
 return tail[0]
state=current()
if state is None:
 assert not members(), 'LOST_LEADER_WITH_ACTIVE_GROUP_STOP_NOT_CONFIRMED'
else:
 root=Path(e['source_root'])
 for name,wanted in e['source_pins'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==wanted
 os.killpg(group,signal.SIGTERM)
 deadline=time.monotonic()+5
 while current() not in {None,'Z'} and time.monotonic()<deadline:time.sleep(0.1)
 if current() not in {None,'Z'}:os.killpg(group,signal.SIGKILL)
 deadline=time.monotonic()+5
 while current() not in {None,'Z'} and time.monotonic()<deadline:time.sleep(0.1)
 assert current() in {None,'Z'}
 # A dead leader alone is insufficient: inspect the process group itself.
 deadline=time.monotonic()+5
 while True:
  active=members()
  if not active:break
  if current()=='Z':os.killpg(group,signal.SIGKILL)
  assert time.monotonic()<deadline
  time.sleep(0.1)
print(json.dumps({'state':'REMOTE_GROUP_STOPPED','pid':pid,'process_group':group,'live_members':0}))
'''


class AuthenticatedSSHTrainingTransport:
    """Owned network adapter; the existing fence/client remain policy owners."""
    def __init__(self, endpoint: SSHTrainingEndpoint):
        self.endpoint = endpoint
        self._channel = None
        self._peer = None
        self._last_stop = None
        self._stderr_thread = None
        self._stderr = bytearray()

    def _command(self, code: str) -> str:
        return shlex.join([self.endpoint.remote_python, '-u', '-c', code])

    def _query(self, code, body, timeout=20):
        result = subprocess.run(self.endpoint.argv(self._command(code)),
            input=json.dumps(body, separators=(',', ':')).encode()+b'\n',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode != 0 or len(result.stdout)>1024*1024:
            raise RemoteTrainingError('AUTHENTICATED_REMOTE_OBSERVATION_FAILED')
        try:
            return json.loads(result.stdout)
        except (ValueError, UnicodeError) as exc:
            raise RemoteTrainingError('REMOTE_OBSERVATION_INVALID') from exc

    def start_stdio(self):
        if self._channel is not None:
            prior = self._last_stop
            if (prior is None or prior['peer'] != self._peer
                    or self._channel.pid != prior['channel_pid']
                    or self._channel.poll() is None
                    or self._channel.returncode != prior['returncode']):
                raise RemoteTrainingError('REMOTE_CHANNEL_ALREADY_STARTED')
            # A closed SSH process is insufficient: recheck the exact preceding
            # remote epoch and group before reusing this retained owner handle.
            current_stop = self._query(_STOP, {'peer':self._peer}, timeout=20)
            if current_stop.get('state') != 'REMOTE_GROUP_STOPPED' or current_stop.get('live_members') != 0:
                raise RemoteTrainingError('REMOTE_STOP_NOT_CONFIRMED')
            for stream in (self._channel.stdin, self._channel.stdout, self._channel.stderr):
                if stream is not None:
                    stream.close()
            self._channel = None
            self._peer = None
        # setsid binds cancellation to this exact owned remote process group.
        command = 'cd '+shlex.quote(self.endpoint.source_root)+' && exec setsid '+shlex.join([
            self.endpoint.remote_python, '-X', 'utf8', '-u', '-m',
            'lumenis.system.ai_gateway.owned_training_runtime', '--remote-managed-training-worker'])
        self._channel = subprocess.Popen(self.endpoint.argv(command), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self._stderr = bytearray()
        incoming = self._channel.stderr
        captured = self._stderr
        def drain_stderr():
            while True:
                block = incoming.read(8192)
                if not block:
                    return
                remaining = 1024 * 1024 - len(captured)
                if remaining > 0:
                    captured.extend(block[:remaining])
        self._stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
        self._stderr_thread.start()
        return self._channel

    def admit_peer(self, hello):
        if self._channel is None or self._channel.poll() is not None:
            raise RemoteTrainingError('REMOTE_CHANNEL_LOST')
        fields={'kind','pid','created_at','source_pins','process_group_id','session_id','proc_start_ticks'}
        if (type(hello) is not dict or set(hello)!=fields or hello.get('kind')!='owned_training_remote_worker_ready'
                or type(hello.get('pid')) is not int or type(hello.get('created_at')) not in {int,float}
                or hello.get('source_pins')!=self.endpoint.source_pins):
            raise RemoteTrainingError('REMOTE_PEER_HELLO_INVALID')
        observed = self._query(_INSPECT, {'pid':hello['pid'], 'source_root':self.endpoint.source_root,
                                         'source_pins':self.endpoint.source_pins})
        if (abs(observed['created_at']-hello['created_at'])>=0.001
                or observed['process_group']!=observed['pid'] or observed['session_id']!=observed['pid']
                or observed['process_group']!=hello['process_group_id']
                or observed['session_id']!=hello['session_id']
                or observed['proc_start_ticks']!=hello['proc_start_ticks']):
            raise RemoteTrainingError('REMOTE_PEER_IDENTITY_MISMATCH')
        self._peer=observed
        return dict(observed)

    def require_live(self):
        if self._peer is None or self._channel is None or self._channel.poll() is not None:
            raise RemoteTrainingError('REMOTE_CHANNEL_LOST')
        fresh=self._query(_INSPECT, {'pid':self._peer['pid'], 'source_root':self.endpoint.source_root,
                                    'source_pins':self.endpoint.source_pins})
        if fresh!=self._peer:
            raise RemoteTrainingError('REMOTE_PEER_CHANGED')
        return dict(fresh)

    def signal_writer_group(self, *, paused):
        if type(paused) is not bool:
            raise RemoteTrainingError('REMOTE_WRITER_STATE_INVALID')
        peer=self.require_live()
        code=_INSPECT+"\nimport signal\nos.killpg(value['process_group'],signal.SIGSTOP if b['paused'] else signal.SIGCONT)\n"
        value=self._query(code, {'pid':peer['pid'],'source_root':self.endpoint.source_root,
                                'source_pins':self.endpoint.source_pins,'paused':paused})
        if value!=peer:
            raise RemoteTrainingError('REMOTE_WRITER_IDENTITY_CHANGED')
        return {'state':'REMOTE_WRITERS_PAUSED' if paused else 'REMOTE_WRITERS_RESUMED',
                'peer':peer}

    def allocate_empty_checkpoint_root(self, remote_root, authorize):
        remote_path(remote_root)
        if not callable(authorize):raise RemoteTrainingError('CURRENT_CHECKPOINT_ADMISSION_REQUIRED')
        authorize();peer=self.require_live()
        result=self._query(_ALLOCATE,{'remote_root':remote_root})
        authorize()
        if self.require_live()!=peer or result!={'remote_root':remote_root,'empty':True}:
            raise RemoteTrainingError('REMOTE_CHECKPOINT_ALLOCATION_NOT_VERIFIED')
        return {'state':'REMOTE_CHECKPOINT_ROOT_ALLOCATED','remote_root':remote_root,'remote_peer':peer}

    def verify_training_inputs(self, paths, expected_files):
        fields={'model_snapshot_dir','train_jsonl_path','heldout_jsonl_path','output_dir','manifest_path'}
        if (type(paths) is not dict or set(paths)!=fields or type(expected_files) is not dict
                or set(expected_files)!=fields-{'output_dir'}):
            raise RemoteTrainingError('REMOTE_TRAINING_INPUT_FIELDS_INVALID')
        for path in paths.values():remote_path(path)
        for key, entries in expected_files.items():
            if type(entries) is not list or not entries or (key!='model_snapshot_dir' and len(entries)!=1):
                raise RemoteTrainingError('REMOTE_TRAINING_INPUT_INVENTORY_INVALID')
            seen=set()
            for entry in entries:
                if (type(entry) is not dict or set(entry)!={'path','role','size_bytes','sha256'}
                        or type(entry['size_bytes']) is not int or entry['size_bytes']<=0
                        or type(entry['role']) is not str or not entry['role']
                        or re.fullmatch(r'[0-9a-f]{64}',str(entry['sha256'])) is None):
                    raise RemoteTrainingError('REMOTE_TRAINING_INPUT_INVENTORY_INVALID')
                name=relative_path(entry['path'])
                if name.casefold() in seen:raise RemoteTrainingError('REMOTE_TRAINING_INPUT_PATH_CONFLICT')
                seen.add(name.casefold())
        peer=self.require_live()
        result=self._query(_VERIFY_INPUTS,{'paths':paths,'files':expected_files},timeout=120)
        if result!={'paths':paths,'files':expected_files} or self.require_live()!=peer:
            raise RemoteTrainingError('REMOTE_TRAINING_INPUTS_CHANGED')
        return {'state':'PHYSICAL_TRAINING_INPUTS_VERIFIED','paths':paths,'files':expected_files,'remote_peer':peer}

    def fetch_checkpoint_bytes(self, *, remote_root, local_root, files, max_bytes, authorize):
        remote_path(remote_root)
        if not callable(authorize) or type(max_bytes) is not int or max_bytes<=0:
            raise RemoteTrainingError('CURRENT_CHECKPOINT_ADMISSION_REQUIRED')
        regular=[]; total=0; seen=set()
        for item in files:
            if (type(item) is not dict or set(item)!={'path','role','size_bytes','sha256'}
                    or type(item['role']) is not str or not item['role']
                    or type(item['size_bytes']) is not int or item['size_bytes']<=0
                    or re.fullmatch(r'[0-9a-f]{64}',str(item['sha256'])) is None):
                raise RemoteTrainingError('CHECKPOINT_INVENTORY_INVALID')
            name=relative_path(item['path'])
            if name.casefold() in seen:raise RemoteTrainingError('CHECKPOINT_PATH_CONFLICT')
            seen.add(name.casefold()); total+=item['size_bytes'];regular.append(item)
        if not regular or total>max_bytes:raise RemoteTrainingError('CHECKPOINT_SIZE_LIMIT')
        if not local_root.is_absolute() or local_root.exists():
            raise RemoteTrainingError('CHECKPOINT_STAGING_ALREADY_EXISTS')
        authorize(); self.require_live()
        local_root.mkdir(parents=True,exist_ok=False)
        copied=[]
        for item in regular:
            authorize(); self.require_live()
            target=local_root.joinpath(*PurePosixPath(item['path']).parts)
            target.parent.mkdir(parents=True,exist_ok=True)
            request={'root':remote_root,'path':item['path'],'bytes':item['size_bytes'],'sha256':item['sha256']}
            process=subprocess.Popen(self.endpoint.argv(self._command(_READ_FILE)),stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            process.stdin.write(json.dumps(request).encode()+b'\n');process.stdin.close()
            digest=hashlib.sha256(); count=0
            try:
                with target.open('xb') as output:
                    while True:
                        block=process.stdout.read(1024*1024)
                        if not block:break
                        count+=len(block)
                        if count>item['size_bytes']:raise RemoteTrainingError('CHECKPOINT_SIZE_MISMATCH')
                        digest.update(block);output.write(block)
                    output.flush();os.fsync(output.fileno())
                if process.wait(timeout=20)!=0 or count!=item['size_bytes'] or digest.hexdigest()!=item['sha256']:
                    raise RemoteTrainingError('CHECKPOINT_BYTES_NOT_VERIFIED')
                authorize(); self.require_live()
                copied.append(dict(item))
            finally:
                if process.poll() is None:process.terminate();process.wait(timeout=10)
        return {'state':'PHYSICAL_CHECKPOINT_BYTES_VERIFIED','source_root':str(local_root),
                'files':copied,'total_bytes':total,'remote_peer':dict(self._peer)}

    def stop_remote_and_reap(self):
        if self._peer is None:
            # Lost before a trusted hello cannot be called a confirmed stop.
            raise RemoteTrainingError('REMOTE_STOP_IDENTITY_NOT_OBSERVED')
        result=self._query(_STOP, {'peer':self._peer},timeout=20)
        if result.get('state')!='REMOTE_GROUP_STOPPED' or result.get('live_members')!=0:
            raise RemoteTrainingError('REMOTE_STOP_NOT_CONFIRMED')
        if self._channel is not None:
            self._channel.stdin.close()
            try:self._channel.wait(timeout=10)
            except subprocess.TimeoutExpired:self._channel.terminate();self._channel.wait(timeout=10)
            if self._channel.poll() is None:
                raise RemoteTrainingError('REMOTE_STOP_NOT_CONFIRMED')
            if self._stderr_thread is not None:
                self._stderr_thread.join(timeout=2)
            self._last_stop = {'remote_stop':dict(result), 'peer':dict(self._peer),
                               'channel_pid':self._channel.pid, 'returncode':self._channel.returncode}
        return result

    def put_checkpoint_bytes(self, *, local_root, remote_root, files, authorize):
        """Rehydrate an immutable Artifact snapshot as actual remote load bytes."""
        remote_path(remote_root)
        if not callable(authorize) or not local_root.is_absolute() or local_root.is_symlink():
            raise RemoteTrainingError('CURRENT_CHECKPOINT_LOAD_ADMISSION_REQUIRED')
        result=[]
        for item in files:
            name=relative_path(item['path'])
            path=local_root.joinpath(*PurePosixPath(name).parts)
            regular_local(path)
            authorize(); self.require_live()
            header={'root':remote_root,'path':name,'bytes':item['size_bytes'],'sha256':item['sha256']}
            process=subprocess.Popen(self.endpoint.argv(self._command(_WRITE_FILE)),stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            digest=hashlib.sha256();count=0
            try:
                process.stdin.write(json.dumps(header).encode()+b'\n')
                with path.open('rb') as source:
                    before=os.fstat(source.fileno())
                    while True:
                        block=source.read(1024*1024)
                        if not block:break
                        count+=len(block);digest.update(block);process.stdin.write(block)
                    after=os.fstat(source.fileno())
                process.stdin.close()
                if (count!=item['size_bytes'] or digest.hexdigest()!=item['sha256']
                        or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)
                        !=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)):
                    raise RemoteTrainingError('CHECKPOINT_IMMUTABLE_SOURCE_CHANGED')
                answer=process.stdout.read(65537)
                if process.wait(timeout=20)!=0 or len(answer)>65536:
                    raise RemoteTrainingError('REMOTE_CHECKPOINT_WRITE_FAILED')
                value=json.loads(answer)
                if value!={'path':name,'size_bytes':item['size_bytes'],'sha256':item['sha256']}:
                    raise RemoteTrainingError('REMOTE_CHECKPOINT_BYTES_NOT_VERIFIED')
                authorize();self.require_live();result.append(value)
            finally:
                if process.poll() is None:process.terminate();process.wait(timeout=10)
        return {'state':'PHYSICAL_REMOTE_LOAD_BYTES_VERIFIED','files':result,'remote_root':remote_root}
