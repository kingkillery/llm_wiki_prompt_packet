---
type: synthesis
title: "Click Deprecation Handling Source-Backed Synthesis"
created: 2026-05-06
updated: 2026-05-06
tags:
  - real-repo
  - click
  - deprecation
  - research-memory
status: developing
related: []
sources:
  - [[click-real-repo-obsidian-001]]
---

# Click Deprecation Handling Source-Backed Synthesis

Fixture repo: `fixtures/click`

Fixture commit: `73e155006526575548d143ef519995f540547e52`

## Question

How does Click handle deprecation warnings across commands, options, arguments, and parser compatibility?

## Evidence

- `fixtures/click/src/click/core.py` defines `ParameterSource`, `Context`, command behavior, and the deprecated `protected_args` compatibility property.
- `fixtures/click/src/click/parser.py` marks parser-level compatibility APIs as deprecated and points argument splitting toward `shell_completion`.
- `fixtures/click/src/click/__init__.py` keeps legacy exports such as `BaseCommand`, `MultiCommand`, `OptionParser`, and `__version__` available while warning that they will be removed.
- `fixtures/click/tests/test_commands.py` covers deprecated command help text and invocation warnings.
- `fixtures/click/tests/test_options.py` covers deprecated option usage, default behavior, required-option rejection, and prompt rejection.
- `fixtures/click/tests/test_arguments.py` covers deprecated argument usage, default behavior, and required-argument rejection.
- `fixtures/click/tests/test_parser.py` and shell-completion tests cover parser compatibility behavior.

## Durable Finding

Click treats deprecation as a user-facing compatibility contract, not just as internal cleanup. Runtime-facing deprecated commands, options, and arguments emit warnings when users actively invoke deprecated behavior, while defaults are generally kept quiet to avoid noisy warnings for implicit behavior. Invalid combinations such as required deprecated parameters or prompted deprecated options are rejected at definition time.

For compatibility APIs, Click leaves legacy symbols and parser helpers importable but warns on access or use. The tests mirror this split: command/option/argument tests verify CLI-visible warning behavior, while parser and shell-completion tests protect migration paths for internal or import-level compatibility.

## Obsidian Save Policy Lesson

This is exactly the kind of analysis that should be saved. It combines code archaeology, test evidence, and a reusable architectural conclusion about a real dependency. Future agents investigating deprecation behavior in CLI frameworks should retrieve this note before repeating the same search.
