# Security

## Reporting a vulnerability

Email **alex@girlea.ro**. Do not open a public issue.

Expect an acknowledgement within 3 working days and a fix or a plan within 30.

## Scope

precommiteu runs entirely on the machine it is installed on: it starts local
`llama-server` processes, talks to them over localhost, and sends nothing to
any network service. Reports of data egress are treated as critical.

Also in scope: sandbox escapes in the file-reading tools, and code execution
via crafted source files or model output.

## Supported versions

The latest release only.
