"""Conservative text/JSON adapters. Unknown or binary formats require a sample."""
import json
import math
import re
from native_import import native_report
from metadata import cinebench_edition, operating_system

MODES = {
    'cb_cpu1': 'CPU Single Core', 'cb_cpux': 'CPU Multi Core',
    'cpu_single_core': 'CPU Single Core', 'cpu_multi_core': 'CPU Multi Core',
    'gpu_score': 'GPU', 'cb_ogl': 'GPU',
}


def parse_measurements(body):
    try:
        text = body.decode('utf-8-sig')
    except UnicodeError:
        try:
            text = body.decode('utf-16')
        except UnicodeError:
            raise ValueError('Nieobsługiwane kodowanie lub format binarny. Potrzebny jest przykładowy plik.') from None
    if '\x00' in text:
        raise ValueError('Nieobsługiwany format binarny.')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    native = native_report(text)
    if native is not None:
        return native
    rows = []
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if isinstance(data, dict) and 'results' in data:
        data = data['results']
    if isinstance(data, dict):
        data = [data]
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                raise ValueError('Nieprawidłowy obiekt wyniku JSON.')
            if ('score' in item and 'test' in item) or any(key in item for key in ('cpu_single','cpu_multi','gpu_score','opengl','shading','opengl_software','opengl_hardware','opengl_standard')):
                rows.append(item)
            else:
                for key, mode in MODES.items():
                    if key in item:
                        rows.append({**item, 'test': mode, 'score': item[key]})
    else:
        # Match explicit named scores only; never guess from arbitrary numbers.
        patterns = [(rf'(?im)^\s*{re.escape(key)}\s*[:=]\s*"?([0-9]+(?:[.,][0-9]+)?)"?\s*(pts|cb|fps)?\s*;?\s*$', mode, 'fps' if key == 'cb_ogl' else '') for key, mode in MODES.items()]
        patterns += [(rf'(?im)^\s*{label}\s*:\s*([0-9]+(?:[.,][0-9]+)?)\s*(pts|cb|fps)?\s*$', mode, '') for label, mode in [(r'CPU\s*\(Single Core\)', 'CPU Single Core'), (r'CPU\s*\(Multi Core\)', 'CPU Multi Core'), ('GPU', 'GPU')]]
        for pattern, mode, default_unit in patterns:
            for match in re.finditer(pattern, text):
                rows.append({'test': mode, 'score': match[1].replace(',', '.'), 'unit': match[2] or default_unit})
    if not rows:
        raise ValueError('Nie rozpoznano wyników. Ten format wymaga adaptera opartego na przykładowym pliku; niczego nie zapisano.')
    output = []
    for item in rows:
        if 'test' not in item:
            output.append(dict(item) | operating_system(item.get('os','')))
            continue
        try:
            score = float(str(item['score']).replace(',', '.'))
        except (ValueError, KeyError, TypeError):
            raise ValueError('Plik zawiera nieprawidłowy wynik.') from None
        if not math.isfinite(score) or score <= 0:
            raise ValueError('Plik zawiera wynik niedodatni lub nieskończony.')
        parsed = dict(item) | {'score': score, 'test': item['test']} | operating_system(item.get('os', ''))
        if not parsed.get('edition') and parsed.get('benchmark_version'):
            parsed['edition'] = cinebench_edition(parsed['benchmark_version'])
        output.append(parsed)
    return output


def parse_report(body):
    from records import combine_measurements
    rows = combine_measurements(parse_measurements(body))
    for row in rows:
        if not row.get('edition') and row.get('benchmark_version'):
            row['edition'] = cinebench_edition(row['benchmark_version'])
    return rows
