"""Rankings are live views over reports; no duplicated or stale ranking records."""
import re
from statistics import mean
from records import METRICS, normalized

DEVICE_METRICS = {'cpu': ('cpu_single','cpu_multi'), 'gpu': tuple(METRICS)[2:]}
EDITION_ORDER = ('2003','R9.5','R10','R11.5','R15','R20','R23','2024','2026')


def edition_key(value):
    return (EDITION_ORDER.index(value) if value in EDITION_ORDER else -1, value)


def version_key(value):
    return (tuple(int(n) for n in re.findall(r'\d+',value)),value)


def check_device(device):
    if device not in DEVICE_METRICS:
        raise ValueError('Wybierz rodzaj sprzętu: cpu lub gpu.')


def ranking(reports, filters):
    device=filters.get('device','cpu')
    check_device(device)
    metrics=DEVICE_METRICS[device]
    requested=filters.get('metric')
    if requested and requested not in metrics:
        raise ValueError('Wybrany test nie należy do tego rankingu sprzętu.')
    named=[r for r in reports if normalized(r[device]) and any(r[k] is not None for k in metrics)]
    editions=sorted({r['edition'] for r in named},key=edition_key,reverse=True)
    edition=filters.get('edition') or next(iter(editions),'')
    selected_reports=[r for r in named if r['edition']==edition]
    available_metrics=[k for k in metrics if any(r[k] is not None for r in selected_reports)]
    default='cpu_multi' if device=='cpu' else 'gpu_score'
    metric=requested or (default if default in available_metrics else next(iter(available_metrics),default))
    measured=[r for r in selected_reports if r[metric] is not None]
    versions=sorted({r['benchmark_version'] for r in measured},key=version_key,reverse=True)
    version=filters.get('benchmark_version',next(iter(versions),''))
    measured=[r for r in measured if r['benchmark_version']==version]
    units=sorted({r[metric+'_unit'] for r in measured})
    unit=filters.get('unit',next(iter(units),''))
    groups={}
    for report in measured:
        if report[metric+'_unit']==unit:
            groups.setdefault(normalized(report[device]),[]).append(report)
    rows=[]
    for key,members in groups.items():
        scores=[r[metric] for r in members]
        rows.append(dict(model=members[0][device],model_key=key,score=mean(scores),
                         best=max(scores),worst=min(scores),count=len(scores)))
    rows.sort(key=lambda row:(-row['score'],row['model_key']))
    previous=None
    for index,row in enumerate(rows,1):
        row['rank']=previous['rank'] if previous and previous['score']==row['score'] else index
        previous=row
    return dict(device=device,editions=editions,metrics=available_metrics,benchmark_versions=versions,units=units,
                selected=dict(edition=edition,metric=metric,benchmark_version=version,unit=unit),rows=rows)


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
    return dict(device=device,model=matching[0][device] if matching else model,record_count=len(matching),
                editions=sorted({r['edition'] for r in matching},key=edition_key,reverse=True),
                reports=matching,summaries=summaries)
