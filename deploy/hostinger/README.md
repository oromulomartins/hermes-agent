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

The hash format is `scrypt$n$r$p$salt$digest`. Keep this value single-quoted
in the deployment `.env`: unquoted dollar signs are interpolated by Compose
and corrupt the hash. After changing credentials, recreate the dashboard
container; a plain restart does not reload its environment.

`deploy.sh` keeps the preceding image reference and restores it when the pull,
startup, or Traefik-routed smoke check fails. It never touches the existing
`hermes` container or the Hostinger catalog Compose directory.
