"""One report per SQL row; measurements remain separate columns."""
import math
from datetime import date
from statistics import mean
from metadata import cinebench_edition, operating_system

METRICS = {
    'cpu_single': 'CPU Single Core', 'cpu_multi': 'CPU Multi Core',
    'gpu_score': 'GPU', 'opengl': 'OpenGL',
    'shading': 'Shading (CINEMA 4D)',
    'opengl_software': 'OpenGL Software Lighting',
    'opengl_hardware': 'OpenGL Hardware Lighting',
    'opengl_standard': 'OpenGL Standard',
}
BY_TEST = {value: key for key, value in METRICS.items()}
META = ('edition','cpu','gpu','threads','os','measured_at','notes','cores','clock_mhz','benchmark_version','system_name','architecture','source_file','os_name','os_version','os_build')
FIELDS = META + tuple(value for key in METRICS for value in (key, key+'_unit'))
UNITS = ('pts','cb','fps','CB-CPU','CB-GFX')


def combine_measurements(rows):
    """Combine measurements from exactly one report; reject ambiguous input."""
    if not rows:
        return []
    report = {key: rows[0].get(key, '') for key in META}
    notes = []
    for row in rows:
        for key in META:
            if key in ('notes',):
                continue
            value = row.get(key, '')
            if value not in ('',None):
                if report.get(key) not in ('',None,value):
                    raise ValueError('Plik zawiera różne konfiguracje. Importuj oddzielne raporty lub użyj CSV.')
                report[key] = value
        if row.get('notes') and row['notes'] not in notes:
            notes.append(row['notes'])
        if 'test' in row:
            key = BY_TEST.get(row['test'])
            if not key:
                raise ValueError('Nieprawidłowy rodzaj testu.')
            if key in report:
                raise ValueError('Powtórzony rodzaj testu w jednym pliku. Nie można jednoznacznie odczytać raportu.')
            report[key], report[key+'_unit'] = row.get('score'), row.get('unit','')
        else:
            for key in METRICS:
                if row.get(key) not in ('',None):
                    if key in report:
                        raise ValueError('Powtórzony wynik w jednym pliku.')
                    report[key], report[key+'_unit'] = row[key], row.get(key+'_unit','')
    report['notes'] = '\n\n'.join(notes)
    return [report]


def validate(raw):
    if not isinstance(raw,dict):
        raise ValueError('Rekord musi być obiektem.')
    if 'test' in raw:
        raise ValueError('Użyj nowego formatu: jeden raport z osobnymi kolumnami wyników.')
    row = {}
    for key in META:
        row[key] = str(raw.get(key) if raw.get(key) is not None else '').strip()
        if len(row[key]) > (20000 if key=='notes' else 255):
            raise ValueError(f'Pole {key} jest za długie.')
    detected = cinebench_edition(row['benchmark_version'])
    entered = cinebench_edition(row['edition'])
    if detected and entered and detected != entered:
        raise ValueError('Edycja Cinebench nie zgadza się z pełną wersją programu.')
    if not row['edition']:
        row['edition'] = detected
    if entered:
        if not row['benchmark_version'] and row['edition'].upper().removeprefix('R') != entered.upper().removeprefix('R'):
            row['benchmark_version'] = row['edition']
        row['edition'] = entered
    if not row['edition'] or not row['cpu']:
        raise ValueError('Podaj wersję Cinebench i procesor.')
    if row['os']:
        row.update(operating_system(row['os']))
    for key in ('cores','threads'):
        try:
            row[key] = int(row[key]) if row[key] else None
            if row[key] is not None and not 1 <= row[key] <= 65536:
                raise ValueError
        except ValueError:
            raise ValueError('Rdzenie i wątki: wymagane liczby całkowite od 1 do 65536.') from None
    try:
        row['clock_mhz'] = float(row['clock_mhz'].replace(',','.')) if row['clock_mhz'] else None
        if row['clock_mhz'] is not None and (not math.isfinite(row['clock_mhz']) or row['clock_mhz']<=0):
            raise ValueError
        if row['measured_at']:
            date.fromisoformat(row['measured_at'])
    except ValueError:
        raise ValueError('Nieprawidłowe MHz lub data (RRRR-MM-DD).') from None
    for key in METRICS:
        value = raw.get(key)
        row[key+'_unit'] = str(raw.get(key+'_unit') or '').strip()
        if value in ('',None):
            row[key] = None
            row[key+'_unit'] = ''
            continue
        try:
            row[key] = float(str(value).replace(',','.'))
        except ValueError:
            raise ValueError(f'Nieprawidłowy wynik: {METRICS[key]}.') from None
        if not math.isfinite(row[key]) or row[key]<=0:
            raise ValueError('Wynik musi być skończoną liczbą większą od zera. Niewykonany test pozostaw pusty.')
        if row[key+'_unit'] not in UNITS:
            raise ValueError(f'Wybierz jednostkę: {METRICS[key]}.')
    return row


def normalized(value):
    return ' '.join((value or '').split()).casefold()


def aggregate(rows, device):
    metrics = list(METRICS)[:2] if device=='cpu' else list(METRICS)[2:] if device=='gpu' else list(METRICS)
    groups = {}
    for row in rows:
        if device in ('cpu','gpu') and not normalized(row[device]):
            continue
        identity = (normalized(row['cpu']),normalized(row['gpu'])) if device=='hardware' else (normalized(row[device]),)
        group_key = (*identity, row['edition'], row['benchmark_version'])
        groups.setdefault(group_key, []).append(row)
    output = []
    for members in groups.values():
        unit_sets = {k:{r[k+'_unit'] for r in members if r[k] is not None} for k in metrics}
        profiles = {}
        for row in members:
            profile = tuple(row[k+'_unit'] if row[k] is not None else next(iter(unit_sets[k])) if len(unit_sets[k])==1 else '' for k in metrics)
            profiles.setdefault(profile, []).append(row)
        for included in profiles.values():
            summary = {key:'' for key in META}
            summary.update(edition=members[0]['edition'],benchmark_version=members[0]['benchmark_version'],report_count=len(included),group_by=device)
            if device=='hardware':
                summary.update(cpu=included[0]['cpu'],gpu=included[0]['gpu'])
            else:
                summary[device]=included[0][device]
            summary['counts']={}
            for key in METRICS:
                values=[r[key] for r in included if key in metrics and r[key] is not None]
                summary[key]=mean(values) if values else None
                summary[key+'_unit']=next((r[key+'_unit'] for r in included if key in metrics and r[key] is not None), '')
                summary['counts'][key]=len(values)
            # Keep empty recognized reports visible in the report list only.
            if any(summary[k] is not None for k in metrics):
                output.append(summary)
    return output
