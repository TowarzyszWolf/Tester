"""Normalize report metadata without guessing the host OS from compatibility data."""
import re


def cinebench_edition(version):
    value = str(version).strip().upper().removeprefix('R')
    for number in ('2003', '2024', '2026', '23', '20', '15', '10', '9.5'):
        if value == number or value.startswith(number + '.') or value.startswith(number + ' '):
            return number if number in ('2003', '2024', '2026') else 'R' + number
    if re.fullmatch(r'11\.5\d*', value):
        return 'R11.5'
    return ''


def operating_system(raw):
    text = str(raw).strip()
    name, version, build = '', '', ''
    build_match = re.search(r'\bbuild\s+([A-Za-z0-9.]+)', text, re.I)
    if build_match:
        build = build_match[1]
    if re.search(r'\bWindows\b', text, re.I):
        name = 'Windows'
        cleaned = re.sub(r'\b(?:32|64)\s*bit\b', '', text, flags=re.I)
        match = re.search(r'Windows\s+(\d+(?:\.\d+)*)', cleaned, re.I)
        if match:
            version = match[1]
            if not build and version.count('.') >= 2:
                build = version.rsplit('.', 1)[1]
    elif re.search(r'\b(?:macOS|Mac OS X|OS X)\b', text, re.I):
        name = 'macOS'
        cleaned = re.sub(r'\b(?:32|64)\s*bit\b', '', text, flags=re.I)
        match = re.search(r'(?:Version\s*|(?:macOS|Mac OS X|OS X)\s*:?\s*)(\d+(?:\.\d+)+)', cleaned, re.I)
        if match:
            version = match[1]
    elif re.search(r'\bLinux\b', text, re.I):
        name = 'Linux'
    return dict(os_name=name, os_version=version, os_build=build)
