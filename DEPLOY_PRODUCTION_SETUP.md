# EarnWage: secure deployment and recovery

Automatic deployment requires EARNWAGE_DEPLOY_ENABLED=true and a completed,
successful API tests workflow triggered by a push to main of
GilPereiraPT/Global-Purchasing-Power-API. Pull requests, forks, other branches,
workflow_run-triggered tests and manual dispatch cannot activate deployment.
The browser Data Manager also requires successful original-repository main-push
tests for the exact SHA. It remains protected by the existing admin token.

## Required configuration (operator action; never enter values in chat)

Keep the existing GitHub Actions secrets EARNWAGE_SSH_HOST, EARNWAGE_SSH_USER,
EARNWAGE_SSH_PORT and EARNWAGE_SSH_PRIVATE_KEY. Add EARNWAGE_SSH_KNOWN_HOSTS
with trusted OpenSSH known_hosts entries obtained and verified through the hosting
provider or another independent trusted channel. For a nonstandard port use
[hostname]:port. Do not obtain trust from ssh-keyscan during deployment. Key
rotation requires independent verification and a deliberate secret update.
SCP and SSH use StrictHostKeyChecking=yes, BatchMode=yes and the dedicated
trusted hosts file. Secret values are written to private files, not echoed or
traced. Do not enable the activation variable until staging validation finishes.

The current target remains /home3/policli1/api-earnwage. Keep that application
root private, outside public_html. The SSH account must own its files and have
python3 (3.11+), tar and disk capacity for staging and code backups. Install the
application dependencies in the Passenger Python environment separately; this
workflow does not change the host-specific virtual environment or install packages.

Set GPP_CACHE_DB and EARNWAGE_INSIGHTS_DB in the existing hosting configuration
to two separate, absolute, persistent, writable SQLite files. Do not substitute
new empty databases for existing production data. No workflow step modifies
secrets, environment files, .htaccess, virtual environments or live databases.

## Packaging and installation

The builder includes tracked app/*.py, scripts/*.py, data/*.json,
passenger_wsgi.py and requirements.txt. It requires the backup, restore,
installer and verifier scripts. It generates app/_release.py in the archive,
without changing source files, and checks that the checkout matches the tested SHA.

The installer validates paths, regular files, sizes, Python syntax, JSON and
required files before installation. Symlinks and private-file paths are rejected.
A private timestamped runtime backup and recovery manifest are mandatory; backup
errors abort installation. A process lock prevents overlapping installers or
runtime recovery. Replaced files use atomic per-file writes; obsolete runtime
files are removed. A write/restart failure attempts runtime recovery and still
returns failure. This is not an atomic swap of the whole application: pause traffic
for sensitive updates and verify in staging.

After requesting a Passenger restart, the workflow requires HTTP 200,
status=ok, the expected application version and the exact commit SHA from
/v1/health. Each worker captures its identity at startup, so an old worker cannot
claim the new SHA by reading a newly replaced marker. Health also checks the two
local SQLite stores. Failure or timeout makes the workflow fail; it does not
trigger automatic rollback after a health failure. Use the procedure below.

The browser deployment response is status=restart_requested: installation and a
restart request are not confirmation of health. Verify its returned commit with
/v1/health before reporting success. A local checkout without release metadata
returns commit=null; it is not accepted as a deployed release.

## Runtime recovery (operator-controlled)

1. Disable EARNWAGE_DEPLOY_ENABLED temporarily and pause traffic/stop Passenger.
2. Select the timestamped code-predeploy-*.tgz from _earnwage_backups; retain it.
3. Run from the application root with a trusted copy of the recovery tool:

   python3 scripts/deploy_runtime.py recover --root /ABSOLUTE/APP_ROOT --archive /ABSOLUTE/APP_ROOT/_earnwage_backups/code-predeploy-TIMESTAMP.tgz

   If the installed tool itself is broken, use the reviewed tool from the matching
   repository release in a private location. The archive restores runtime files
   and previous commit identity and removes newly introduced runtime files. It
   never restores databases or hosting configuration. Restart is requested.
4. Resume Passenger and verify /v1/health against the recovered version/SHA.
   Pre-Phase-2 backups can lack SHA metadata: manually verify their identity;
   do not report them as a verified SHA release.
5. Investigate the original failure before resuming traffic/automatic deployment.

Code backup retention is manual. Preserve enough known-good releases and monitor
disk capacity. These backups are runtime recovery, not off-host disaster recovery.

## Data backup and recovery (separate from runtime rollback)

Use the application's Python environment from the application root:

python -m scripts.backup_earnwage_data --output /PRIVATE/NEW_BACKUP_DIRECTORY

The existing SQLite online-backup procedure validates integrity and records SHA256
checksums. All available data/*.json snapshots are included. The destination is
private and must not already exist. Store another copy off-host under the
operator's existing backup policy.

python -m scripts.restore_earnwage_data --backup /PRIVATE/BACKUP_DIRECTORY --output /PRIVATE/NEW_RECOVERY_DIRECTORY

Recovery validates BOTH database checksums/integrity and snapshot checksums before
writing. It only creates a new private recovery directory, never overwrites live
databases and never edits environment configuration. With Passenger stopped,
inspect the recovered data; then an operator may deliberately switch the hosting
DB paths or replace database files following the hosting's maintenance procedure.
Handle old WAL/SHM files while all writers are stopped. Restart, verify health and
representative data, and keep the original databases for recovery. JSON snapshots
are recovery copies; adopting them in the application is a separate operator action.

## Validation before enabling deployment

Run python -m pytest -q (Python dependencies from requirements.txt and Node.js 22
for the actual browser release-verification regression; CI installs Node explicitly). Tests build the actual workflow package, install it in
an empty temporary directory, perform real SQLite backup/recovery, simulate
installation failure/runtime rollback, reject unsafe archives and check commit
verification. They use temporary data and mocked HTTP; no production deployment,
SSH connection, secret update or live database operation is performed.

In staging, verify the trusted SSH host entry, Python environment, permissions,
Passenger restart, health SHA and the manual recovery procedure. Only after review
and staging validation should an operator enable EARNWAGE_DEPLOY_ENABLED=true.
