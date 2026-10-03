"""Stage an explicit research-file allowlist and upload a draft GitHub Release backup.
No recursive cache upload. Large files are split into 512 MiB parts; SHA-256 hashes
allow restoration by concatenating the listed parts in order and checking the file.
"""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/pypsa-eur'
STAGE=DATA/'release-backup-20261001'
TAG='research-2025-checkpoint-20261001'
REPO='autological-eu/grid-conductor'
FILES=[DATA/'monthly-weather/europe-2025-compact.nc',DATA/'monthly-weather/annual-verified.json',DATA/'upstream/data/cutout/build/unknown/europe-2025-hydro.nc',DATA/'upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc',DATA/'resource-pilot-march-2025-ipm.nc',DATA/'march-ipm-pilot-status.json',DATA/'annual-ipm-solve-status.json']
FILES+=sorted((DATA/'monthly-weather').glob('2025-*/verified.json'))
FILES+=list((ROOT/'config/pypsa-eur').glob('*.yaml'))
FILES+=[DATA/'upstream/pixi.lock',DATA/'upstream/scripts/add_electricity.py',DATA/'upstream/scripts/_helpers.py',DATA/'upstream/scripts/gridfix_compact_cutout.py']
def call(args):
 result=subprocess.run(args,text=True,capture_output=True)
 if result.returncode:
  raise RuntimeError(result.stderr[:2000])
 return result.stdout

def main():
 STAGE.mkdir(exist_ok=True)
 manifest={'schema_version':1,'repository':REPO,'source_commit':call(['git','-C',str(ROOT),'rev-parse','HEAD']).strip(),'status':'prepared_2025_inputs_and_March_pilot_not_annual_solution','restore':'Concatenate each file parts in listed order, verify file SHA-256, then restore to its relative path. Restore compact weather to its original path; recreate the upstream cutout symlink. Never treat the March pilot as an annual result.','assumptions':['2024 country-level nuclear availability proxy','March solution closes storage over March; annual solve stopped at memory guard'],'files':[]}
 for source in FILES:
  if not source.is_file():raise ValueError(f'Required file absent: {source}')
  rel=str(source.relative_to(ROOT));name=rel.replace('/','__');parts=[];digest=hashlib.sha256();size=0
  with source.open('rb') as stream:
   number=0
   while True:
    block=stream.read(512*1024*1024)
    if not block:break
    name_part=f'{name}.part-{number:03d}';dest=STAGE/name_part
    dest.write_bytes(block);digest.update(block);size+=len(block)
    parts.append({'asset':name_part,'bytes':len(block),'sha256':hashlib.sha256(block).hexdigest()});number+=1
  manifest['files'].append({'path':rel,'bytes':size,'sha256':digest.hexdigest(),'parts':parts})
  print('Staged',rel,flush=True)
 path=STAGE/'manifest.json';path.write_text(json.dumps(manifest,indent=2)+'\n')
 notes=STAGE/'README.md';notes.write_text('Prepared 2025 ERA5/atlite research inputs and a March-only dispatch pilot. No full annual solved network. Source attribution and model assumptions remain in the repository research docs and manifest. Data collected from Copernicus ERA5; PyPSA-Eur contributors supplied the build pipeline. Nuclear availability uses a declared 2024 proxy. Assets are checksummed in manifest.json; concatenate parts in listed order to restore. Credentials and raw temporary caches are excluded.\n')
 result=subprocess.run(['gh','release','view',TAG,'--repo',REPO],capture_output=True)
 if result.returncode:
  call(['gh','release','create',TAG,'--repo',REPO,'--target',manifest['source_commit'],'--draft','--title','2025 prepared research checkpoint','--notes-file',str(notes)])
 for row in manifest['files']:
  for part in row['parts']:
   call(['gh','release','upload',TAG,str(STAGE/part['asset']),'--repo',REPO,'--clobber']);print('Uploaded',part['asset'],flush=True)
 call(['gh','release','upload',TAG,str(path),str(notes),'--repo',REPO,'--clobber'])
 remote=json.loads(call(['gh','release','view',TAG,'--repo',REPO,'--json','assets']))
 assets={a['name']:a['size'] for a in remote['assets']}
 for row in manifest['files']:
  for part in row['parts']:assert assets.get(part['asset'])==part['bytes']
 print('All uploaded asset sizes verified; draft backup complete.',flush=True)

if __name__=='__main__':main()
