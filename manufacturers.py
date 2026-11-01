"""Recognize chip designers from model names; leave ambiguous names unknown."""
import re

UNKNOWN = 'Nieznany'
CPU_PATTERNS = (
    ('Intel', r'\b(?:intel|xeon|celeron|pentium|atom)\b|\bcore\s+(?:i[3579]\b|2\b|ultra\b)'),
    ('AMD', r'\b(?:amd|advanced micro devices|ryzen|athlon|epyc|threadripper|opteron|sempron|phenom|turion|duron)\b'),
    ('Apple', r'\bapple\b|^m\d+(?:\s+(?:pro|max|ultra))?$'),
    ('Qualcomm', r'\b(?:qualcomm|snapdragon|oryon)\b'),
    ('Samsung', r'\b(?:samsung|exynos)\b'),
    ('MediaTek', r'\b(?:mediatek|dimensity)\b'),
    ('VIA', r'\b(?:via|centaur)\b'),
    ('IBM', r'\bibm\b'),
    ('Motorola', r'\bmotorola\b'),
    ('Freescale', r'\bfreescale\b'),
    ('Loongson', r'\bloongson\b'),
    ('Hygon', r'\bhygon\b'),
    ('Zhaoxin', r'\bzhaoxin\b'),
    ('SiFive', r'\bsifive\b'),
)
GPU_PATTERNS = (
    ('NVIDIA', r'\b(?:nvidia|geforce|quadro|tesla|nvs|rtx|gtx)\b'),
    ('Intel', r'\b(?:intel|iris|arc)\b|\b(?:uhd|hd) graphics\b'),
    ('ATI', r'\bati\b|\brage\b'),
    ('AMD', r'\b(?:amd|advanced micro devices|radeon|firepro|firegl)\b'),
    ('Apple', r'\bapple\b|^m\d+(?:\s+(?:pro|max|ultra))?$'),
    ('Qualcomm', r'\b(?:qualcomm|adreno|snapdragon)\b'),
    ('Arm', r'\bmali\b'),
    ('Imagination', r'\b(?:powervr|imagination)\b'),
    ('Matrox', r'\bmatrox\b'),
    ('3dfx', r'\b(?:3dfx|voodoo)\b'),
    ('S3', r'\b(?:s3|savage)\b'),
    ('XGI', r'\bxgi\b'),
    ('SiS', r'\bsis\b'),
)


def manufacturer(model, device):
    value=' '.join((model or '').replace('_',' ').split())
    if device=='gpu':
        # Explicit chip branding takes precedence over a generic family name.
        for name,pattern in (('NVIDIA',r'\bnvidia\b'),('Intel',r'\bintel\b'),('ATI',r'\bati\b'),('AMD',r'\b(?:amd|advanced micro devices)\b'),('Apple',r'\bapple\b')):
            if re.search(pattern,value,re.I):
                return name
    patterns=CPU_PATTERNS if device=='cpu' else GPU_PATTERNS
    for name,pattern in patterns:
        if re.search(pattern,value,re.I):
            return name
    return UNKNOWN
