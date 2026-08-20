#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE = Path('/config/custom_components/markvarec_work_agenda/normalize.py')
spec = importlib.util.spec_from_file_location('markvarec_work_agenda_normalize', MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)

raw = {
    'generated_at': '2026-08-20T16:00:00+02:00',
    'source_status': 'ok',
    'open_count': 17,
    'urgent_count': 2,
    'overdue_count': 3,
    'today_count': 1,
    'mail_attention_count': 1,
    'mail_body': 'THIS MUST NEVER REACH HA',
    'html': '<b>secret</b>',
    'credentials': {'token': 'secret'},
    'items': [
        {
            'id': 'abc123',
            'title': 'Client task',
            'project': 'Benefit Palace',
            'workspace': 'client',
            'status': 'to do',
            'priority': 'urgent',
            'due': '2026-08-21',
            'url': 'https://app.clickup.com/t/abc123',
            'mail_body': 'DROP ME',
            'description': 'DROP ME TOO',
        },
        {
            'id': 'bad-url',
            'title': 'Bad URL must be stripped',
            'priority': 'weird',
            'url': 'https://evil.example.test/',
        },
    ] + [
        {'id': f'extra{i}', 'title': f'Extra {i}', 'url': f'https://app.clickup.com/t/extra{i}'}
        for i in range(20)
    ],
}

out = mod.normalize_snapshot(raw)
assert set(out) == {
    'generated_at', 'source_status', 'open_count', 'urgent_count',
    'overdue_count', 'today_count', 'mail_attention_count', 'items'
}
assert out['source_status'] == 'ok'
assert out['open_count'] == 17
assert out['mail_attention_count'] == 1
assert len(out['items']) == mod.MAX_ITEMS
assert out['items'][0] == {
    'id': 'abc123',
    'title': 'Client task',
    'project': 'Benefit Palace',
    'workspace': 'client',
    'status': 'to do',
    'priority': 'urgent',
    'due': '2026-08-21',
    'url': 'https://app.clickup.com/t/abc123',
    'source': 'clickup',
}
assert 'mail_body' not in out['items'][0]
assert 'description' not in out['items'][0]
assert out['items'][1]['url'] == ''
assert out['items'][1]['priority'] == 'none'

bad = mod.normalize_snapshot({'open_count': -2, 'source_status': 'nonsense'})
assert bad['open_count'] == 0
assert bad['source_status'] == 'unknown'

try:
    mod.normalize_snapshot('not-an-object')
except ValueError:
    pass
else:
    raise AssertionError('non-object snapshot must be rejected')

print('WORK_AGENDA_REGRESSION_OK')
