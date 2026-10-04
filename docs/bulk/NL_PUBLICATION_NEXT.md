# CBS history: production reconciliation prerequisite

The authenticated Data Manager salary inventory export now includes all stored rows of nl_cbs_wages when the table exists. Absent tables are explicitly marked absent without initializing them. The same read-only transaction, ZIP checksums, private storage, token protection, and size/time budgets are reused. Stored identities, publication status, hourly unit, employee count and precision are preserved.

This change requires no merge of PR #35. It does not publish salaries, initialize tables, create a new importer or change existing snapshots. The reviewed CBS dataset and source page are explicitly allowed; malformed metadata fails closed.

## Operator step

After this PR is integrated, update the runtime through the existing Data Manager code update process and restart the Python app if required. Use the existing salary inventory download button and provide the resulting ZIP for reconciliation. No terminal commands are needed. The manifest must identify nl_cbs_wages as exported or absent.

The existing US/CA export cannot establish which CBS historical observations are missing. PR #35 reports 243 additional accepted records compared with the Git snapshot, not production. Its full reviewed raw bundle and staging are needed to construct a reproducible package; these private files are not in this checkout.

## Remaining implementation

After obtaining the refreshed inventory and reviewed CBS bundle: reconcile full target identities, units, classification, population and revisions; add a validated CBS projection to the existing bulk_publication mechanism; build a missing-only package from accepted staging; preserve quarantine and existing rows; test preview, writer-lock recheck, apply, idempotence and guarded rollback against an isolated target model. Keep existing upload/checksum approval, fresh backup and recovery gates. No production publication is performed by this PR.
