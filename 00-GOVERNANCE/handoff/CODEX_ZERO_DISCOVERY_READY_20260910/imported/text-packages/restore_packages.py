from pathlib import Path
import base64, hashlib, json

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / 'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
for pkg in MANIFEST['packages']:
    folder = ROOT / pkg['label']
    payload = ''.join((folder / name).read_text(encoding='ascii') for name in pkg['parts'])
    data = base64.b64decode(payload)
    digest = hashlib.sha256(data).hexdigest()
    if digest != pkg['sha256']:
        raise SystemExit(f"SHA256 mismatch for {pkg['original_name']}: {digest} != {pkg['sha256']}")
    out = ROOT / pkg['original_name']
    out.write_bytes(data)
    print(f"RESTORED {out.name} sha256={digest} size={len(data)}")
