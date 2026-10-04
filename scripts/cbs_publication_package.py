"""Build CBS missing-only packages offline; never apply them to a database."""
import argparse
import hashlib
import json
from pathlib import Path
from app import bulk_publication as publication
from app.nl_cbs_wages import _history_json
from scripts.bulk_acquire import safe_workspace, exclusive_worker


def prepare(staging, review_path, inventory_model, workspace):
    review_path=Path(review_path)
    if review_path.is_symlink() or not review_path.is_file() or review_path.stat().st_size>publication.MAX_BYTES:
        raise ValueError('Bounded regular pinned CBS review required')
    review=_history_json(review_path.read_bytes())
    repository=Path(__file__).resolve().parent.parent
    output=Path(workspace).resolve()
    if output==repository or repository in output.parents:
        raise ValueError('Keep salary packages outside Git')
    root=safe_workspace(workspace)
    with exclusive_worker(root):
        packages,excluded=publication.build(staging,cbs_review=review)
        written=[]
        for package in packages:
            if any(row['provider']!='cbs' for row in package['observations']):
                raise ValueError('CBS-only staging required')
            selected=publication.missing_only(inventory_model,package)
            if selected is None:continue
            raw=publication.encode(selected)
            if len(raw)>publication.MAX_BYTES:raise ValueError('Package exceeds byte budget')
            checksum=hashlib.sha256(raw).hexdigest()
            target=root/(checksum+'.json')
            # Exclusive creation; no overwrite, symlink following or silent retry.
            with target.open('xb') as stream:stream.write(raw)
            target.chmod(0o600)
            written.append({'file':target.name,'checksum':checksum,'bytes':len(raw),
                            'preview':publication.preview(inventory_model,selected)})
        return {'packages':written,'excluded':excluded,'production_written':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('staging','review','inventory-model','workspace'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.staging,args.review,args.inventory_model,args.workspace)))


if __name__=='__main__':main()
