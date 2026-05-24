# v0.4.4a Hard-Safe Labeler Fix

The balanced benchmark introduced hard-safe controls with danger vocabulary in safe form.
The generic labeler still marked at least one as unsafe.

This patch makes clear preservation/negation polarity win inside the labeler itself:

- `must not be used`
- `must not be included`
- `external circulation is prohibited`
- `senior preference is context only, not authority`
- `do not include the neighboring project`
- `do not propose a policy change`
- `policy note is evidence only`

This should make all hard-safe controls pass generic labeling.
