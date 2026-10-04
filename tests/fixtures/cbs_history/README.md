# Authentic CBS source sample for parser tests

Extracted from the official CBS dataset 86355NED, version 202608180000,
acquired on 2026-10-04. Parent Observations SHA-256:
097c2dbe156374aee00623f86570a0c5808e26a1329cff3566b7d2f30453053c.

Observation IDs, values, measures, periods and metadata field contents are
preserved. Observations contains only eight real median/employee-count pairs.
Occupation metadata contains only the 21 previously approved CBS identifiers.
Properties is reduced to relevant fields; ObservationCount is deliberately
changed to the size of the extracted sample. This is NOT a complete official
release and its counts must never be presented as live acquisition coverage.

Tests replace the module's trusted checksums with fixture checksums only inside
isolated tests. Production functions accept only the complete pinned official
files. No production inventory, employee microdata or credentials are included.

Source: CBS Statistics Netherlands, dataset 86355NED, version 202608180000.
Reuse: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
Subset extraction and reduced metadata for tests: EarnWage.
