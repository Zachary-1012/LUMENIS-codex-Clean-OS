"""Run the frozen SecurityScanner class only in a disposable fake source root."""
from __future__ import annotations
import ast, datetime, hashlib, json, logging, os, pathlib, re, socket, subprocess, sys, tempfile
root, output=map(pathlib.Path,sys.argv[1:3])
BASE='01588e9fd9568e3fcaf1e6c3d957bc498436fa48'
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],timeout=10).decode().strip()==BASE
raw=(root/'security_scanner.py').read_bytes()
blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
node=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='SecurityScanner')
def denied(*a,**k):raise RuntimeError('AUDIT_NETWORK_FORBIDDEN')
socket.socket.connect=denied;socket.socket.connect_ex=denied;socket.create_connection=denied
with tempfile.TemporaryDirectory(prefix='lumenis-scanner-probe-') as directory:
    namespace={'os':os,'sys':sys,'re':re,'json':json,'hashlib':hashlib,'subprocess':subprocess,'datetime':datetime.datetime,'logger':logging.getLogger('audit'),'__file__':str(pathlib.Path(directory)/'scanner_fixture.py')}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'security_scanner.py','exec'),namespace)
    scanner=namespace['SecurityScanner']()
    empty=scanner.full_scan()
    fake='AUDIT_ONLY_NOT_A_REAL_CREDENTIAL_0001'
    (pathlib.Path(directory)/'fixture.py').write_text('api_key = '+repr(fake)+'\n',encoding='utf-8')
    (pathlib.Path(directory)/'fixture.dart').write_text('void main() {}\n',encoding='utf-8')
    selected=scanner._get_scan_files()
    sensitive=scanner.scan_sensitive_info()
    record={'baseline':BASE,'observed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'source_blob':blob,'boundary':'FULL_CLASS_IN_DISPOSABLE_FIXTURE_ROOT_NOT_PRODUCT_E2E','source_modified':False,'production_data_accessed':False,'results':{'empty_scan':{'integrity_status':empty['integrity']['status'],'dependency_status':empty['dependencies']['status'],'scanned_files':empty['dangerous_code']['scanned_files'],'overall_status':empty['overall_status'],'overall_risk':empty['overall_risk']},'dart_in_scan':any(p.endswith('.dart') for p in selected),'py_in_scan':any(p.endswith('.py') for p in selected),'synthetic_credential_returned_in_preview':any(fake in f.get('preview','') for f in sensitive['findings']),'actual_credentials_read':False}}
    (output/'security-probes.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False,indent=2))
