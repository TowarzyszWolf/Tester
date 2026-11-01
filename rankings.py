"""Rankings are live views over reports; no duplicated or stale ranking records."""
import re
from statistics import mean
from records import METRICS, normalized
from manufacturers import manufacturer, UNKNOWN

DEVICE_METRICS = {'cpu': ('cpu_single','cpu_multi'), 'gpu': tuple(METRICS)[2:]}
EDITION_ORDER = ('2003','R9.5','R10','R11.5','R15','R20','R23','2024','2026')


def edition_key(value):
    return (EDITION_ORDER.index(value) if value in EDITION_ORDER else -1, value)


def version_key(value):
    return (tuple(int(n) for n in re.findall(r'\d+',value)),value)


def check_device(device):
    if device not in DEVICE_METRICS:
        raise ValueError('Wybierz rodzaj sprzętu: cpu lub gpu.')


def ranking_unit(edition,metric,reports):
    if metric in DEVICE_METRICS['cpu']:
        if edition in ('2003','R9.5','R10'):
            return 'CB-CPU'
        if edition in ('R11.5','R15'):
            return 'cb'
        if edition in ('R20','R23','2024','2026'):
            return 'pts'
        units=[row[metric+'_unit'] for row in reports]
        return min(set(units),key=lambda unit:(-units.count(unit),unit)) if units else ''
    if metric=='gpu_score':
        return 'pts'
    return 'fps' if metric=='opengl' else 'CB-GFX'


def compatible_unit(unit,expected,device):
    # cb/pts/CB-CPU are labels for CPU points, not different scales within an edition.
    return unit==expected or (device=='cpu' and unit in ('cb','pts','CB-CPU') and expected in ('cb','pts','CB-CPU'))


def ranking(reports, filters):
    device=filters.get('device','cpu')
    check_device(device)
    metrics=DEVICE_METRICS[device]
    requested=filters.get('metric')
    if requested and requested not in metrics:
        raise ValueError('Wybrany test nie należy do tego rankingu sprzętu.')
    sort=filters.get('sort','score')
    if sort=='manufacturer':
        sort='manufacturer_asc'
    if sort not in ('score','manufacturer_asc','manufacturer_desc'):
        raise ValueError('Nieprawidłowy sposób sortowania rankingu.')
    named=[r for r in reports if normalized(r[device]) and any(r[k] is not None for k in metrics)]
    editions=sorted({r['edition'] for r in named},key=edition_key,reverse=True)
    edition=filters.get('edition') or next(iter(editions),'')
    selected_reports=[r for r in named if r['edition']==edition]
    available_metrics=[k for k in metrics if any(r[k] is not None for r in selected_reports)]
    default='cpu_multi' if device=='cpu' else 'gpu_score'
    metric=requested or (default if default in available_metrics else next(iter(available_metrics),default))
    measured=[r for r in selected_reports if r[metric] is not None]
    unit=ranking_unit(edition,metric,measured)
    groups={}
    excluded=0
    for report in measured:
        if compatible_unit(report[metric+'_unit'],unit,device):
            groups.setdefault(normalized(report[device]),[]).append(report)
        else:
            excluded+=1
    rows=[]
    for key,members in groups.items():
        scores=[r[metric] for r in members]
        rows.append(dict(model=members[0][device],model_key=key,manufacturer=manufacturer(members[0][device],device),score=mean(scores),
                         best=max(scores),worst=min(scores),count=len(scores)))
    rows.sort(key=lambda row:(-row['score'],row['model_key']))
    previous=None
    for index,row in enumerate(rows,1):
        row['rank']=previous['rank'] if previous and previous['score']==row['score'] else index
        previous=row
    manufacturers=sorted({row['manufacturer'] for row in rows},key=lambda name:(name==UNKNOWN,name.casefold()))
    selected_manufacturer=filters.get('manufacturer','')
    if selected_manufacturer:
        rows=[row for row in rows if normalized(row['manufacturer'])==normalized(selected_manufacturer)]
        selected_manufacturer=next((name for name in manufacturers if normalized(name)==normalized(selected_manufacturer)),selected_manufacturer)
    if sort!='score':
        known=[row for row in rows if row['manufacturer']!=UNKNOWN]
        unknown=[row for row in rows if row['manufacturer']==UNKNOWN]
        rows=sorted(known,key=lambda row:row['manufacturer'].casefold(),reverse=sort=='manufacturer_desc')+unknown
    return dict(device=device,editions=editions,metrics=available_metrics,unit=unit,manufacturers=manufacturers,
                excluded_unit_count=excluded,
                selected=dict(edition=edition,metric=metric,manufacturer=selected_manufacturer,sort=sort),rows=rows)


def hardware_history(reports,device,model):
    check_device(device)
    if not normalized(model):
        raise ValueError('Podaj nazwę modelu sprzętu.')
    matching=[r for r in reports if normalized(r[device])==normalized(model)]
    matching.sort(key=lambda r:(edition_key(r['edition']),version_key(r['benchmark_version']),r['measured_at'],r['id']),reverse=True)
    groups={}
    for row in matching:
        for metric in DEVICE_METRICS[device]:
            if row[metric] is not None:
                key=(row['edition'],row['benchmark_version'],metric,row[metric+'_unit'])
                groups.setdefault(key,[]).append(row[metric])
    summaries=[dict(edition=e,benchmark_version=v,metric=m,unit=u,score=mean(scores),count=len(scores))
               for (e,v,m,u),scores in groups.items()]
    summaries.sort(key=lambda r:(edition_key(r['edition']),version_key(r['benchmark_version']),r['metric'],r['unit']),reverse=True)
    name=matching[0][device] if matching else model
    return dict(device=device,model=name,manufacturer=manufacturer(name,device),record_count=len(matching),
                editions=sorted({r['edition'] for r in matching},key=edition_key,reverse=True),
                reports=matching,summaries=summaries)
