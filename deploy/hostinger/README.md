# Hostinger deployment

This Compose project is deliberately independent from the catalog-managed Hermes
deployment. It runs only the dashboard process, has its own named volume, does
not publish host ports, and joins Traefik's existing external network.

The GitHub workflow writes the runtime `.env` on the VPS with mode `0600`.
Required GitHub secrets are documented in `.github/workflows/deploy-hostinger.yml`.
The dashboard password must be an scrypt hash, never plaintext. Generate one
with the Hermes image or a local checkout:

```sh
python -c "from plugins.dashboard_auth.basic import hash_password; print(hash_password('choose-a-password'))"
```

The hash format is `scrypt$n$r$p$salt$digest`. The workflow uses `write-env.sh`
to quote credentials and escape dollar signs for Compose; GitHub secrets must
contain the original values, without added quotes or escaping. Unquoted dollar
signs are interpolated by Compose and corrupt credentials. The writer rejects
multiline input and preserves raw IMAGE/TRAEFIK_HOST for `deploy.sh`.
After changing credentials, recreate the dashboard container; a plain restart
does not reload its environment. `deploy-config-tests.yml` exercises the real
Compose parser on pull requests without deployment credentials or a deploy.

`deploy.sh` leaves the active deployment unchanged on pull failure and restores
the preceding image and configuration if replacement validation fails. It never touches the existing
`hermes` container or the Hostinger catalog Compose directory.

## Transactional upgrades and recovery evidence

The workflow uploads a unique `incoming/<workflow-run>-<attempt>/` bundle containing
`docker-compose.next.yml`, `.env.next` and the deployment scripts; it does not
replace the active configuration during upload. `deploy.sh` invokes `deploy.py`
with a host-side exclusive lock. Python 3 and Docker Compose are required on the
VPS. This upgrade path requires an existing healthy dashboard; initial provisioning
and schema-changing migrations need a separate plan.

Before changing the live container, the deployment:

1. Checks the active image, configured environment, expected volume and SQLite
   integrity, and runs an HTTPS session journey through the public endpoint.
2. Pulls the candidate and resolves its immutable image ID. A pull failure leaves
   the active configuration untouched.
3. Stops only `hermes-agent-rm` briefly, archives `/opt/data` (including SQLite WAL)
   and copies the complete previous dotenv/Compose definition, then starts it again.
   Backups live in `backups/<run>/` with private permissions. They contain secrets
   and user data and must never be uploaded as CI artifacts. No automatic retention
   deletion is performed; operators must account for disk use.
4. Restores the archive into a new disposable volume, with no network access, and
   boots previous → candidate → previous in distinct containers. Each must pass
   synthetic password login, authenticated identity/dashboard/session-list access,
   logout, SQLite integrity and unchanged schema/record checks. Credentials are
   synthetic; existing app secrets are not sent to CI. A candidate that changes
   schema or stored records fails closed before live replacement.
   Startup maintenance timestamps and the lazily recorded FTS format marker are
   excluded from the record comparison; goal/loop metadata remains protected. This
   conservative gate is appropriate for this deployment-only fix, not arbitrary
   data migrations.
5. Applies the candidate image ID and complete candidate configuration to the live
   dashboard, preserving the named volume. On failure, it restores the previous
   image ID **and full configuration**, validates the restored app, and still exits
   nonzero. It never restores a backup over live data or deletes the live volume.

`python3 incoming/<run>-<attempt>/deploy.py --directory "$PWD"
--candidate-dir incoming/<run>-<attempt> --rehearse-only` runs the same preflight, consistent backup and
isolated recovery rehearsal, without replacing the live app. It still briefly
stops the dashboard to capture the backup. No shared Traefik/catalog service is
changed. The rehearsal proves recovery of a copy; the receipt separately records
whether the live app was deployed or actually rolled back. Live validation checks
SQLite integrity, database presence and compatible schemas, allowing legitimate
concurrent record changes. Exact record preservation is proven only on the isolated
copy; it is not asserted for a live database that remains writable.

The public smoke requires valid TLS, denies anonymous identity access, checks
`/api/auth/me`, `/api/sessions` and `/`, and verifies logout clears the client
session. Because the VPS stores a password **hash**, this probe creates a short-lived
session inside the container using the existing provider. It does not claim a new
human password login. Password login is exercised on the isolated copy; the previous
human confirmation remains separate evidence. No tokens or response bodies are logged.

`receipts/<run>.json` and `receipt.json` contain sanitized image IDs, rehearsal
container IDs and outcomes (`deployed`, `rehearsal_passed`, `rolled_back`,
`rollback_failed`, `backup_restart_failed`, `failed_before_replace`). The workflow
publishes only the receipt matching its SHA and run/attempt. A red job with
`rolled_back` means recovery succeeded, not deployment success. A failed recovery
requires incident handling; the private backup is preserved. Abrupt host loss or
SIGKILL cannot be recovered by an in-process handler and requires reconciliation.

Run the PR checks, including real Docker replacement of a synthetic service:

```sh
HERMES_DEPLOY_DOCKER_TESTS=1 scripts/run_tests.sh deploy/hostinger --file-timeout 600
```

These tests use disposable containers and SQLite history, not staging credentials.
They exercise the controller against a small HTTP service fixture; the CD rehearsal
executes the actual previous/candidate Hermes images and actual copied data.
