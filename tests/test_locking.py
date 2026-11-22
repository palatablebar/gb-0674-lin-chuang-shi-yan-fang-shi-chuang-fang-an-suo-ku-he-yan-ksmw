from app.modules.locking.rules import decide
from copy import deepcopy

def test_clean_lockable(clean):
    assert clean['balance']['status']=='可锁库'
def test_dirty_blocks(sample):
    assert sample['balance']['blocked']==7;assert sample['balance']['status']=='待处理'
def test_input_conservation(sample):
    assert sample['balance']['input']==53;assert sample['balance']['accepted']==47;assert sample['balance']['quarantined']==3;assert sample['balance']['row_balanced']
def test_completed_expected(clean):
    assert clean['balance']['completed']==42;assert clean['balance']['expected']==44
def test_pending_not_blocking(clean):
    assert clean['balance']['pending']==2;assert clean['balance']['due']==42;assert clean['balance']['status']=='可锁库'
def test_dirty_pending_not_blocking(sample):
    assert sample['balance']['pending']==2;assert sample['balance']['blocked']==7
def test_isolation_blocks(clean):
    s=deepcopy(clean);s['quarantine']=[{'id':'x'}];assert decide(s)['status']=='待处理'
def test_count_mismatch_blocks(clean):
    s=deepcopy(clean);s['counts']['input']+=1;assert decide(s)['status']=='待处理';assert decide(s)['row_balanced'] is False
def test_missing_visit_not_replaced(sample):
    assert sample['balance']['completed']==40;assert sample['balance']['expected']==44
