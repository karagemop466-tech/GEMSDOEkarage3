"""Restore core owner-mirror data via the pinned, unchanged canonical restoration tool.

Hashes establish mirror integrity, NOT organizer authenticity. Large files stay ignored.
This wrapper does not create a model, feature stack, candidate, or score.
"""
import importlib.util
import json
import math

if __package__:
    from .audit_historical_rasters import ROOT, SNAPSHOT, canonical_validator
else:
    from audit_historical_rasters import ROOT, SNAPSHOT, canonical_validator


def main():
    # Verify every pinned file before executing upstream code.
    canonical_validator()
    spec = importlib.util.spec_from_file_location('canonical_restore', SNAPSHOT / 'scripts/restore_data.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = json.loads((SNAPSHOT / 'registry/data_manifest.json').read_text())
    results = []
    for row in manifest['files']:
        if row['group'] == 'core':
            result = module.restore_entry(row, ROOT / 'data')
            results.append(result)
            print(row['id'], result['status'], result['bytes'], flush=True)
    import rasterio
    grids = []
    with rasterio.open(ROOT / 'data/sample_submission.tif') as template:
        expected = (template.crs, template.shape, template.transform)
    for row in results:
        with rasterio.open(ROOT / 'data' / row['dest']) as ds:
            match = (ds.crs, ds.shape, ds.transform) == expected
            if not match:
                raise ValueError(f'Core mirror geometry mismatch: {row["id"]}')
            grids.append(dict(id=row['id'], crs=str(ds.crs), shape=list(ds.shape),
                              transform=list(ds.transform)[:6], bands=ds.count,
                              descriptions=list(ds.descriptions),
                              nodata=ds.nodata if ds.nodata is not None and math.isfinite(ds.nodata) else None,
                              nodata_repr=str(ds.nodata), template_geometry_match=match))
    receipt = dict(provenance='Owner mirrors only; verified against pinned upstream SHA256, not authenticated against organizer host',
                   canonical_tool='evidence/template-inspection/scripts/restore_data.py', files=results, grids=grids)
    (ROOT / 'docs/core-data-receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
