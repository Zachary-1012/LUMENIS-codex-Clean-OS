# Third-party materials

This specification baseline ships no third-party runtime, vendored source, model
weights or font binaries. It does not grant rights to any material in Git history.

## Development methods

[The repository pstack skill](.agents/skills/oevira-pstack/SKILL.md) adapts selected
engineering methods from Lauren Tan's pstack 0.15.36, revision
`1ba91fc25c0977741dd0e267849e6234b037ed0a` of `cursor/plugins`.
Its [MIT copyright and license](.agents/skills/oevira-pstack/LICENSE) are retained.
The adaptation keeps task-specific correction, domain modeling, caller-first
architecture, impact verification, direct outcome checks and benchmarking;
it omits upstream model routing, installers, hooks and autonomous effects.
This is development guidance, not an additional product runtime or integration.

Before adopting an already planned component, record its exact version/source,
license, modifications and attribution requirements alongside the actual usage.
Preserve required original notices in distributed packages. Product, code, data,
model weights and media rights must not be conflated.

Historical notices are retained verbatim in
[docs/reference/THIRD_PARTY_NOTICES.md](docs/reference/THIRD_PARTY_NOTICES.md).
Their old relative links address the immutable pre-rebuild tree linked from
[the reference index](docs/reference/README.md), not this new source tree.

The root [LICENSE](LICENSE) is unchanged. Self-developed product logic does not
imply that third-party components have been relicensed or privately owned.
