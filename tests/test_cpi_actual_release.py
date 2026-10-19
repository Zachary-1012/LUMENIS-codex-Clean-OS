from pathlib import Path
import hashlib
import pytest
from lumenis.importer import macro
ROOT=Path(__file__).resolve().parent
# Exact retained official release, retrieved 2026-10-18; factual source fixture, not synthetic data.
TEXT=(ROOT/'fixtures/nbs_cpi_202609.txt').read_text()
URL='https://www.stats.gov.cn/english/PressRelease/202610/t20261015_1965500.html'
def test_real_cpi_source_exact_units_period_and_locator():
 r=macro.parse_nbs_release(TEXT,source_url=URL);assert len(r['facts'])==1
 f=r['facts'][0];assert (f['value'],f['unit'],f['period_start'],f['period_end'])==('0.9','percent_yoy','2026-09-01','2026-09-30')
 q=TEXT[f['locator']['start']:f['locator']['end']];assert 'increased by 0.9% year on year' in q
 assert hashlib.sha256(q.encode()).hexdigest()==f['locator']['quote_sha256']
 assert f['publication_timezone']=='UNKNOWN'
@pytest.mark.parametrize('lead',["China’s Consumer Price Index (CPI) decreased by 0.9% year on year","China's Consumer Price Index (CPI) decreased by 0.9 percent year on year",'the national consumer price index (CPI) decreased by 0.9 percent year on year'])
def test_legacy_and_bounded_new_variants(lead):
 r=macro.parse_nbs_release('Consumer Price Index in September 2026\nIn September 2026, '+lead,source_url=URL)
 assert r['facts'][0]['value']=='-0.9'
@pytest.mark.parametrize('bad',['month on month','year on yearly','percentage points year on year','% month on month'])
def test_wrong_measure_never_becomes_yoy(bad):
 t='Consumer Price Index in September 2026\nIn September 2026, China’s Consumer Price Index (CPI) increased by 0.9 '+bad
 assert macro.parse_nbs_release(t,source_url=URL)['facts']==[]
@pytest.mark.parametrize('lead',['In August 2026, China’s Consumer Price Index (CPI) increased by 0.9% year on year','In September 2025, China’s Consumer Price Index (CPI) increased by 0.9% year on year','In September 2026, China’s Consumer Price Index (CPI) increased by UNKNOWN% year on year','In September 2026, food consumer price index (CPI) increased by 0.9% year on year'])
def test_period_unknown_subindex_rejected(lead):
 assert macro.parse_nbs_release('Consumer Price Index in September 2026\n'+lead,source_url=URL)['facts']==[]
def test_conflicting_current_leads_abstain():
 t='Consumer Price Index in September 2026\nIn September 2026, China’s Consumer Price Index (CPI) increased by 0.9% year on year.\nIn September 2026, the national consumer price index (CPI) increased by 0.8 percent year on year.'
 assert macro.parse_nbs_release(t,source_url=URL)['missing'][0]['reason']=='RELEASE_OBSERVATIONS_AMBIGUOUS'
