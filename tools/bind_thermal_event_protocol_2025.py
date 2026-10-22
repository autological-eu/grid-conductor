"""Bind revised pre-solve orchestration to unchanged sealed physical arrays.

The first driver stopped at its protocol hash guard, before any solver call.
The preparer never uses protocol fields to construct physical inputs. Preserve
that original receipt and bind the revised declaration explicitly, not in place.
"""
import json
from pathlib import Path
from prepare_thermal_event_2025 import OUT,ROOT
from generation_mix_2025 import digest

def bind():
    old=OUT/'inputs.json';meta=json.loads(old.read_text());new=OUT/'inputs-protocol-v2.json';assert not new.exists()
    assert meta['producer_sha256']==digest(ROOT/'tools/prepare_thermal_event_2025.py')
    for file,sha in meta['files'].items():assert digest(OUT/file)==sha
    design='config/thermal-event-2025.json'
    for file,sha in meta['source_hashes'].items():
        if file!=design:assert digest(ROOT/file)==sha
    assert not list((OUT/'runs-v1').glob('*.npz')),'Never rebind completed experiments'
    meta['source_hashes'][design]=digest(ROOT/design)
    meta['protocol_binding']=dict(parent_file='inputs.json',parent_sha256=digest(old),producer_file=Path(__file__).name,producer_sha256=digest(__file__),reason='48h lookahead and consistent initial-state protocol revised before any solve; physical arrays unchanged')
    new.write_text(json.dumps(meta,indent=2)+'\n')
if __name__=='__main__':bind()
