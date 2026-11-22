from collections import defaultdict
from datetime import datetime, time, timezone, timedelta
from app.coerce import instant, caldate
from app.modules.protocol.rules import choose_protocol

ZONE=timezone(timedelta(hours=8))

def expected_close(subject,visit,context,cutoff):
    # 未发生访视的预期窗口按截止时刻有效方案计，窗止日=入组日历日+窗终日。
    moment=datetime.combine(cutoff,time(23,59,59),tzinfo=ZONE)
    plan=choose_protocol(subject,moment,context)
    start,end=context['plans'][plan][visit]
    enrolled=instant(context['subjects'][subject]).astimezone(ZONE).date()
    return plan,enrolled+timedelta(days=end)

def detect(windows,context):
    cutoff=caldate(context.get('cutoff',''))
    primary=defaultdict(list)
    for row in windows:
        if row['kind']=='PRIMARY':primary[(row['subject'],row['visit'])].append(row)
    issues=[];completed=[];pending=[]
    for subject in sorted(context['subjects']):
        for visit in context['required_visits']:
            items=primary.get((subject,visit),[])
            if len(items)>1:
                issues.append({'subject':subject,'visit':visit,'id':','.join(r['id'] for r in items),'code':'DUPLICATE_PRIMARY'});continue
            plan,close=expected_close(subject,visit,context,cutoff)
            due=close<=cutoff
            if not items:
                entry={'subject':subject,'visit':visit,'id':'','close_day':close.isoformat(),'selected_protocol':plan}
                if due:issues.append({**entry,'code':'MISSING_PRIMARY'})
                else:pending.append({**entry,'code':'PENDING_MATURITY','detail':f'窗口{close.isoformat()}才止，本批未到期'})
                continue
            row=items[0]
            if row['code']=='IN_WINDOW':completed.append(row)
            elif due:issues.append({**row,'code':'WINDOW_'+row['code']})
            else:pending.append({'subject':subject,'visit':visit,'id':row['id'],'close_day':close.isoformat(),'selected_protocol':plan,'code':'PENDING_MATURITY','detail':f'已回传记录窗外({row["code"]})，窗口{close.isoformat()}才止'})
    return issues,completed,pending

def apply(state):
    issues,completed,pending=detect(state['windows'],state['context']);state.update(deviations=issues,completed=completed,pending=pending)
    state['views']['deviation']={'title':'偏离复核','rows':issues,'metrics':{'完成访视':len(completed),'缺失或偏离':len(issues),'缺首次访视':sum(x['code']=='MISSING_PRIMARY' for x in issues),'待成熟':len(pending)}}
