from app.modules.archive.rules import freeze
from app.archive import serialize
from copy import deepcopy
import zipfile,io,json

def test_clean_frozen(clean):
    assert clean['archive']['status']=='可冻结'
def test_dirty_not_frozen(sample):
    assert sample['archive']['status']=='待处理'
def test_subject_count(clean):
    assert clean['archive']['subjects']==22;assert clean['archive']['results']==42
def test_archive_carries_cutoff_and_pending(clean):
    assert clean['archive']['cutoff']=='2026-11-17';assert clean['archive']['pending']==2
def test_locked_state_propagates(clean):
    s=deepcopy(clean);s['balance']['status']='待处理';assert freeze(s)['status']=='待处理'
def test_seal_covers_results(clean):
    s=deepcopy(clean);s['selected_results'][0]['value_mg_dl']='999';assert freeze(s)['seal']!=clean['archive']['seal']
def test_seal_covers_cutoff(clean):
    s=deepcopy(clean);s['context']['cutoff']='2026-11-18';assert freeze(s)['seal']!=clean['archive']['seal']
def test_seal_covers_pending(clean):
    s=deepcopy(clean);s['pending']=[];assert freeze(s)['seal']!=clean['archive']['seal']
def test_bundle_has_evidence(sample):
    z=zipfile.ZipFile(io.BytesIO(serialize(sample)));d=json.loads(z.read('evidence.json'));assert len(d['quarantine'])==3
def test_bundle_shows_scope_pending_and_blockers(sample):
    z=zipfile.ZipFile(io.BytesIO(serialize(sample)))
    manifest=json.loads(z.read('manifest.json'));evidence=json.loads(z.read('evidence.json'))
    assert manifest['cutoff']=='2026-11-17'
    assert len(evidence['pending'])==2;assert evidence['balance']['blocked']==7;assert evidence['balance']['due']==42
def test_manifest_digest(clean):
    z=zipfile.ZipFile(io.BytesIO(serialize(clean)));assert json.loads(z.read('manifest.json'))['sha256']==clean['manifest']['sha256']
