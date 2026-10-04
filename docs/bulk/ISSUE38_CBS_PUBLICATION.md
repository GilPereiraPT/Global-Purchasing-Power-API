# Issue 38 — CBS historical salary publication

## Implementation and dependencies

This integration branch includes the unchanged PR #35 CBS staging/history implementation and adds CBS to the existing bulk_publication mechanism. PR #36 inventory support is already in main. No separate production importer or endpoint is introduced. Packages retain the v1 schema, with an optional cbs_review evidence object. Existing BLS/Job Bank packages remain unchanged.

Every CBS row must exactly reproduce its row and original provenance from the independently pinned full history review. Pinned record and review hashes cannot be replaced by caller-supplied checksums. The approved 202608180000 release, licence, metadata and source artifact hashes are enforced. The specific warehouse_operator 2023 observation held in PR #35 remains inadmissible even if submitted directly.

Only accepted complete staging enters build. The offline missing_only operation omits identical existing rows and rejects any numerical or metadata revision. CBS comparison covers all stored fields, including employee count, publication status, concept, classification and precision. Data Manager repeats comparison under writer lock and keeps existing authorization/checksum, preview, fresh backup, recovery and guarded rollback gates. Nothing enables bulk publication automatically.

## Actual evidence and rehearsal

The owner supplied the four-table export dated 2026-10-04T16:16:17.388862+00:00. It has 21 CBS rows matching the Git snapshot in all 20 fields. CRC, permitted/unique members, JSON keys, schemas, primary identities, byte counts and SHA-256 were checked. No production database connection was made.

Five fresh official HTTP downloads in this task matched every independently pinned raw checksum from PR #35. The reconstructed review preserves the earlier acquisition timestamps in that PR; these are not the new download timestamps. Staging reproduction returned 264 accepted, one quarantined and eight absent profession/year combinations. Full raw files, review, staging, owner inventory and model databases stay private outside Git.

The missing-only canonical package is 595371 bytes and has 243 historical rows, zero duplicates and zero protected conflicts in preview. SHA-256: 5b1e8c2dd407ef10b54845a553c9bdca56a6da6a43af8dfa30cf0a6d6cf5476f. Existing 21 rows remain unchanged. Rehearsal on a private model rebuilt from the export inserted 243, produced 264 total rows, repeated as already_published, passed SQLite integrity_check and rolled back exactly the 243 additions to the original 21. No production writes occurred. No additional professions or annual salaries are claimed.

## Operator flow (browser only)

After review/CI and integration, update server code through the existing Data Manager and restart the Python application as appropriate. This branch already includes PR #35; do not merge the same changes twice without checking the final diff.

In Data Manager, upload the delivered JSON salary package, compare the displayed SHA-256 to the value above, and run preview. Expected counts: 243 new rows, zero duplicates, zero protected rows. If counts differ, stop and repeat reconciliation against a new inventory. Use the existing backup/recovery checks and review the concrete checksum before publication. The file alone does not authorize or execute publication. Afterwards download a fresh inventory to verify the 264 rows and preservation of the 21 originals.

## Reproduction by Codex

Use scripts.cbs_publication_package with explicit --staging, --review, --inventory-model and --workspace paths. Output is private, outside Git. The inventory model is built offline from the authorized export. This command reads the model and never applies a package. Repeat evidence validation before generating another package.
