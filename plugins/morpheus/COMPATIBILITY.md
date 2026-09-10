# Morpheus compatibility

This plugin was verified against Hermes Agent commit
`abec17e1be660f46e505a11c386573f35f58ecc6`.

## Contract

- The plugin uses the native general-plugin contract: `plugin.yaml` plus
  `register(ctx)`.
- It registers only namespaced surfaces: `morpheus_status` and
  `/morpheus-status`.
- Discovery has no external side effects. No worker, scheduler, or kanban
  integration is started unless a future explicitly configured feature does so.
- No Hermes core patch is required for this version.

The plugin is opt-in through `plugins.enabled: [morpheus]` in the Hermes
configuration.
