"""Prepare small salary packages offline; never contact or import production."""
import argparse
import hashlib
import json
from pathlib import Path
from app.bulk_publication import build,encode


def export(staging,output,limit=1000):
    output=Path(output)
    if output.is_symlink() or output.exists() or 'public_html' in output.resolve().parts:
        raise ValueError('Choose a new private package directory')
    packages,excluded=build(staging,limit)
    output.mkdir(parents=True,mode=0o700)
    index=[]
    for package in packages:
        raw=encode(package);checksum=hashlib.sha256(raw).hexdigest()
        path=output/(checksum+'.json');path.write_bytes(raw);path.chmod(0o600)
        index.append({'checksum':checksum,'file':path.name,'bytes':len(raw),
                      'observations':len(package['observations'])})
    manifest={'schema':'earnwage-salary-package-index-v1','packages':index,'excluded':excluded,
              'note':'Preparation only; no production comparison or publication. Review exact checksums and scopes.'}
    (output/'index.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--staging',required=True);parser.add_argument('--output',required=True);parser.add_argument('--limit',type=int,default=1000)
    args=parser.parse_args();print(json.dumps(export(args.staging,args.output,args.limit)))
