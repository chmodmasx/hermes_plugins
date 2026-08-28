# gitea-professional 2.0.0

Hermes skill for professional Gitea 1.27.x operation. In the full integration bundle this skill is the policy/knowledge layer for the native `gitea-hermes` plugin; detailed material is progressively loaded from `references/`.

Primary interface order:

1. native `gitea_*` tools for Gitea control-plane operations;
2. normal Git over SSH for source/history/working-tree work;
3. bundled scripts only as a fallback or for explicitly advanced operations.

The skill also includes deep Gitea Actions workflow/runner/security guidance, templates, a workflow auditor, a defensive stdlib API client and offline tests.

When using the full bundle, install from the bundle root with `./install.sh`. Standalone skill installation remains possible with this directory's `install.sh`, but does not provide native tools by itself.

Run offline tests with:

```bash
python -m unittest discover -s tests -v
```
