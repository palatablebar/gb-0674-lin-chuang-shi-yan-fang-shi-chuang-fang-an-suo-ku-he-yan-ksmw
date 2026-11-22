from fastapi.testclient import TestClient
from app import main,store
from app.engine import evaluate
import pytest

def client(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DB_PATH',str(tmp_path/'test.sqlite'));return TestClient(main.app)
def test_api_idempotent(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);a=c.post('/api/runs',json={}).json();b=c.post('/api/runs',json={}).json();assert a['manifest']['run_id']==b['manifest']['run_id'];assert len(c.get('/api/runs').json())==1
def test_stale_review(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);a=c.post('/api/runs',json={}).json();url='/api/runs/'+a['manifest']['run_id']+'/review';assert c.post(url,json={'revision':1}).status_code==200;assert c.post(url,json={'revision':1}).status_code==409
def test_seven_entries(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    for k in main.MODULES:
        assert c.post('/api/'+k,json={}).status_code==200
        assert c.get('/'+k).status_code==200
def test_bad_dataset(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);assert c.post('/api/runs',json={'dataset':'../bad'}).status_code==422
def test_missing_run(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);assert c.get('/api/runs/none').status_code==404
def test_restart_store(tmp_path,sample):
    p=str(tmp_path/'durable.sqlite');store.save(p,sample);assert store.get(p,sample['manifest']['run_id'])['manifest']['sha256']==sample['manifest']['sha256']
def test_bad_revision(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch);s=c.post('/api/runs',json={}).json();assert c.post('/api/runs/'+s['manifest']['run_id']+'/review',json={'revision':0}).status_code==422

def test_clean_navigation_run_preserved(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    run=c.post('/api/runs',json={'dataset':'clean'}).json()
    rid=run['manifest']['run_id']
    for k in main.MODULES:
        html=c.get('/'+k+'?run_id='+rid).text
        assert '?run_id='+rid in html
        assert rid in html
    assert c.get('/api/export/'+rid).status_code==200

def test_custom_csv_snapshot_and_navigation(tmp_path,monkeypatch):
    from app.config import ROOT
    c=client(tmp_path,monkeypatch)
    original=(ROOT/'sample_data/clean.csv').read_text()
    # 改成独立于所有仓内样例的证据编号，追踪其跨页与重跑行为。
    first=original.splitlines()[1].split(',')[0]
    custom=original.replace(first,first+'-CUSTOM')
    result=c.post('/api/runs',json={'csv_text':custom}).json()
    rid=result['manifest']['run_id']
    assert '-CUSTOM' in str(result['records']) or '-CUSTOM' in str(result['quarantine'])
    for key in main.MODULES:
        response=c.get('/'+key+'?run_id='+rid)
        assert response.status_code==200
        assert '?run_id='+rid in response.text
    repeated=c.post('/api/runs/'+rid+'/rerun',json={})
    assert repeated.status_code==200
    assert repeated.json()['manifest']['run_id']==rid
    assert repeated.json()['manifest']['sha256']==result['manifest']['sha256']

def test_boundary_switch_creates_new_batch_and_keeps_old(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    a=c.post('/api/runs',json={'dataset':'clean'}).json()
    b=c.post('/api/runs',json={'dataset':'clean','overrides':{'cutoff':'2026-11-18'}}).json()
    rid_a,rid_b=a['manifest']['run_id'],b['manifest']['run_id']
    assert rid_a!=rid_b
    assert a['balance']['pending']==2 and a['balance']['status']=='可锁库'
    assert b['balance']['pending']==0 and b['balance']['deviations']==2 and b['balance']['status']=='待处理'
    kept=c.get('/api/runs/'+rid_a).json()
    assert kept['context']['cutoff']=='2026-11-17' and kept['balance']['pending']==2
    assert len(c.get('/api/runs').json())==2

def test_rerun_keeps_frozen_boundary(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    a=c.post('/api/runs',json={'dataset':'clean'}).json()
    c.post('/api/runs',json={'dataset':'clean','overrides':{'cutoff':'2026-11-18'}})
    again=c.post('/api/runs/'+a['manifest']['run_id']+'/rerun',json={}).json()
    assert again['manifest']['run_id']==a['manifest']['run_id']
    assert again['context']['cutoff']=='2026-11-17' and again['balance']['pending']==2

def test_boundary_switch_failure_restores_old(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    a=c.post('/api/runs',json={'dataset':'clean'}).json()
    rid=a['manifest']['run_id']
    failed=c.post('/api/runs',json={'dataset':'clean','overrides':{'cutoff':'11/17/2026'}})
    assert failed.status_code==422 and failed.json()['code']=='BAD_CUTOFF'
    history=c.get('/api/runs').json()
    assert len(history)==1 and history[0]['id']==rid
    kept=c.get('/api/runs/'+rid).json()
    assert kept['context']['cutoff']=='2026-11-17'
    assert kept['input_snapshot']['bytes_b64']==a['input_snapshot']['bytes_b64']

def test_pages_show_scope_pending_and_blockers(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    run=c.post('/api/runs',json={}).json()
    rid=run['manifest']['run_id']
    for key in ('deviation','locking','archive'):
        html=c.get('/'+key+'?run_id='+rid).text
        assert '2026-11-17' in html and '待成熟' in html and 'PENDING_MATURITY' in html
        assert 'MISSING_PRIMARY' in html
    export=c.get('/api/export/'+rid)
    assert export.status_code==200
    import zipfile,io,json
    z=zipfile.ZipFile(io.BytesIO(export.content))
    manifest=json.loads(z.read('manifest.json'));evidence=json.loads(z.read('evidence.json'))
    assert manifest['cutoff']=='2026-11-17'
    assert len(evidence['pending'])==2 and evidence['balance']['blocked']==7
