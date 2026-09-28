# EarnWage automatic production deployment

This repository can deploy the production API automatically after the **API tests**
workflow succeeds on `main`.

## Production path

`/home3/policli1/api-earnwage`

The workflow only packages tracked runtime files from:

- `app/*.py`
- `data/*.json`
- `passenger_wsgi.py`
- `requirements.txt`

It does **not** deploy SQLite databases, `.htaccess`, environment variables,
backups, virtual environments or other server-private files.

Before extraction, the server replaces
`_earnwage_backups/code-predeploy-latest.tgz` with a backup of the previous
runtime code/data state. Passenger is restarted by touching `tmp/restart.txt`.
The workflow then checks `/v1/health` and requires the production version to
match the tested commit.

## GitHub configuration

In **Settings -> Secrets and variables -> Actions**, create these repository
**Secrets**:

- `EARNWAGE_SSH_HOST` — SSH hostname supplied by the hosting provider.
- `EARNWAGE_SSH_USER` — cPanel/SSH user.
- `EARNWAGE_SSH_PORT` — SSH port, often 22 but use the hosting value.
- `EARNWAGE_SSH_PRIVATE_KEY` — private deployment key. Store the complete
  private key only as a GitHub Secret; never commit or paste it into source.

Then create this repository **Variable**:

- `EARNWAGE_DEPLOY_ENABLED` = `true`

Keep it absent or set to `false` until SSH access has been configured and
tested.

## First activation

1. Confirm SSH access is enabled in the hosting/cPanel account.
2. Add the four Secrets above.
3. Set `EARNWAGE_DEPLOY_ENABLED=true`.
4. Open **Actions -> Deploy production API -> Run workflow** for the first test.
5. Confirm that the health check finishes successfully.
6. From then on, every successful **API tests** run on `main` triggers an
   automatic production deployment.

## Dependencies

The workflow synchronizes `requirements.txt`, but deliberately does **not**
run `pip install` because the CloudLinux/cPanel virtual-environment path is
hosting-specific. If a future commit adds or changes Python dependencies,
update the Python App environment separately before enabling that deployment.
