from app.modules.deviation.rules import detect
from copy import deepcopy

def test_missing_primary_real(sample):
    assert any(r['subject']=='00020' and r['code']=='MISSING_PRIMARY' for r in sample['deviations'])
def test_late_deviation_real(sample):
    assert any(r['id']=='00001-V1' and r['code']=='WINDOW_LATE' for r in sample['deviations'])
def test_clean_completed_real(clean):
    assert len(clean['completed'])==42;assert clean['deviations']==[]
def test_pending_maturity_real(clean):
    # TRAP-26 未到期访视不判漏访
    pending={(r['subject'],r['visit']):r for r in clean['pending']}
    assert set(pending)=={('00021','V2'),('00022','V2')}
    assert all(r['code']=='PENDING_MATURITY' and r['close_day']=='2026-11-18' for r in pending.values())
def test_due_gap_still_blocks(sample):
    assert not any(r['subject']=='00020' for r in sample['pending'])
    assert any(r['subject']=='00020' and r['visit']=='V2' and r['close_day']=='2026-10-18' for r in sample['deviations'])
def test_cutoff_switch_matures(clean):
    # 边界后移，待成熟转为已到期缺口
    context=deepcopy(clean['context']);context['cutoff']='2026-11-18'
    issues,completed,pending=detect(clean['windows'],context)
    assert pending==[];assert len([r for r in issues if r['code']=='MISSING_PRIMARY'])==2
def test_cutoff_switch_forward_keeps_pending(clean):
    context=deepcopy(clean['context']);context['cutoff']='2026-11-12'
    issues,completed,pending=detect(clean['windows'],context)
    assert len(pending)==2;assert len(completed)==42
def test_retest_cannot_fill_missing(clean):
    rows=[r for r in clean['windows'] if r['id']!='00001-V1'];issues,done,pending=detect(rows,clean['context']);assert any(r['subject']=='00001' and r['visit']=='V1' and r['code']=='MISSING_PRIMARY' for r in issues)
def test_duplicate_primary_blocks(clean):
    rows=clean['windows']+[dict(clean['windows'][0],id='DUPLICATE')];issues,done,pending=detect(rows,clean['context']);assert issues[0]['code']=='DUPLICATE_PRIMARY';assert len(done)==41
def test_order_invariant(clean):
    assert detect(clean['windows'],clean['context'])==detect(list(reversed(clean['windows'])),clean['context'])
def test_retest_not_counted_as_visit(clean):
    assert len([r for r in clean['windows'] if r['kind']=='RETEST'])==5;assert len(clean['completed'])==42
