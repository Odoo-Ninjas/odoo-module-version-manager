# Selbst gehosteter Runner

Der Release-Workflow verwendet nach dem Organisationsumzug Linux-x64-Runner
mit dem zusätzlichen Label `zebroo-tools`. Die Organisationsgruppe wird auf
die 16 umgezogenen Repositories beschränkt. Der Workflow läuft nur bei Pushes
auf `main`; diese Umstellung löst keinen Release-Test auf einem PR aus.

Aktivierung erst nach Prüfung des Runner-Rollouts in Ticket 5697 und einem
Smokejob auf dem neuen Runner. Die YAML-Syntax wird lokal geprüft; ein
PyPI-Release ist kein geeigneter Smoke-Test. Rückweg ist ein Revert dieses PRs.
