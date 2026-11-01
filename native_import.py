"""Adapters verified against the user's native Cinebench 2003–2026 reports."""
import math
import re


def edition_name(value):
    value = value.upper().removeprefix('R')
    return value if value in ('2003', '2024', '2026') else 'R' + value


def number(value, field):
    try:
        result = float(value.replace(',', '.'))
    except ValueError:
        raise ValueError(f'Nieprawidłowa liczba w polu {field}.') from None
    if not math.isfinite(result) or result < 0:
        raise ValueError(f'Nieprawidłowa liczba w polu {field}.')
    return result


def native_report(text):
    """Return None for an unrelated format, [] for a recognized empty report."""
    modern = re.search(r'(?im)^COMMENT=These are your MAXON CINEBENCH R(11\.5|15|20|23|2024|2026) results\.', text)
    legacy = re.search(r'(?im)^CINEBENCH\s+(2003(?:\s+v\d+)?|9\.5|R10)\s*$', text)
    if not modern and not legacy:
        return None
    rows = []
    if modern:
        fields = {}
        for line in text.splitlines():
            key, sep, value = line.partition('=')
            if not sep or key == 'COMMENT':
                continue
            if key in fields:
                raise ValueError(f'Powtórzone pole {key} w raporcie.')
            fields[key] = value.strip()
        edition = edition_name(modern[1])
        cores = fields.get('CORES', '')
        threads = fields.get('THREADS', '')
        if not threads and cores and fields.get('LOGICALCORES'):
            # R11.5/R15 store logical threads per physical core.
            threads = str(int(cores) * int(fields['LOGICALCORES']))
        extra_keys = ('C4DBUILDID', 'OPENGLVENDOR', 'OPENGLVERSION', 'DRIVERVERSION', 'GPUVENDOR', 'GPUAPI')
        notes = [f'{key}={fields[key]}' for key in extra_keys if fields.get(key)]
        common = dict(edition=edition, cpu=fields.get('PROCESSOR', ''),
                      gpu=fields.get('GPUCARD') or fields.get('OPENGLCARD', ''),
                      cores=cores, threads=threads, clock_mhz=fields.get('MHZ', ''),
                      os=fields.get('OSVERSION', ''), system_name=fields.get('C4DINFO', ''),
                      architecture=fields.get('CBTYPE', ''), benchmark_version=fields.get('C4DVERSION', ''))
        for key, mode, unit in (
            ('CBCPU1', 'CPU Single Core', 'cb' if edition in ('R11.5', 'R15') else 'pts'),
            ('CBCPUX', 'CPU Multi Core', 'cb' if edition in ('R11.5', 'R15') else 'pts'),
            ('CBOPENGL', 'OpenGL', 'fps'), ('CBGPU', 'GPU', 'pts'),
        ):
            if key not in fields:
                continue
            score = number(fields[key], key)
            if score == 0:
                continue
            details = notes + [f'Pole wyniku: {key}']
            # Peaks and arrays describe the same run, not additional results.
            for meta in (key + 'PEAK', key + 'ARRAY', 'CBOPENGLQUALITY' if key == 'CBOPENGL' else ''):
                if meta and fields.get(meta):
                    details.append(f'{meta}={fields[meta]}')
            rows.append(common | dict(test=mode, score=score, unit=unit, notes='\n'.join(details)))
    else:
        edition = edition_name(legacy[1].split()[0])
        fields = {}
        for line in text.splitlines():
            key, sep, value = line.partition(':')
            if sep:
                fields[key.strip()] = value.strip()
        common = dict(edition=edition, cpu=fields.get('Processor', ''), gpu=fields.get('Graphics Card', ''),
                      threads=fields.get('Number of CPUs', ''), os=fields.get('Operating System', ''),
                      system_name=fields.get('Tester', ''), benchmark_version=legacy[1])
        # The legacy report labels logical rendering workers as Number of CPUs;
        # it does not establish a physical-core count.
        mhz = fields.get('MHz', '')
        frequency = re.fullmatch(r'([\d.,]+)\s*(GHz|MHz)?', mhz, re.I)
        if frequency:
            common['clock_mhz'] = number(frequency[1], 'MHz') * (1000 if (frequency[2] or '').lower() == 'ghz' else 1)
        modes = [
            (r'Rendering\s*\(Single\s+CPU\)', 'CPU Single Core', 'CB-CPU'),
            (r'Rendering\s*\(Multiple\s+CPU\)', 'CPU Multi Core', 'CB-CPU'),
            (r'Shading\s*\(CINEMA 4D\)', 'Shading (CINEMA 4D)', 'CB-GFX'),
            (r'Shading\s*\(OpenGL Software Lighting\)', 'OpenGL Software Lighting', 'CB-GFX'),
            (r'Shading\s*\(OpenGL Hardware Lighting\)', 'OpenGL Hardware Lighting', 'CB-GFX'),
            (r'Shading\s*\(OpenGL Standard\)', 'OpenGL Standard', 'CB-GFX'),
        ]
        for pattern, mode, unit in modes:
            match = re.search(rf'(?im)^\s*{pattern}\s*:\s*(---|[\d.,]+)\s+{unit}\s*$', text)
            if not match or match[1] == '---':
                continue
            score = number(match[1], mode)
            if score:
                rows.append(common | dict(test=mode, score=score, unit=unit, notes=f'MHz (z pliku): {mhz}'))
    return rows
