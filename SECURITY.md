# Security

## Secrets

The repository does not contain production tokens, passwords, payment
credentials, customer data, server addresses, or private access links.

Create `.env` from `.env.example` and provide your own values locally.
Never commit `.env`, database dumps, Telegram session files, or generated
user files.

## Reporting

Please report a suspected security issue privately to maksim.zolotuhin@inbox.ru. Do not
publish credentials or customer data in a public issue.

## Demo status

This is a portfolio demo. Production deployment requires additional
hardening, monitoring, backups, rate limiting, access control, and a
security review appropriate to the target environment.
