# Security Policy

## Project status

Safegloss Legacy is an in-development legacy project and does not currently
publish supported release versions. Do not deploy it with real student,
teacher, research, or production data without an independent security and
privacy review.

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities, credentials, or personal
data in a public issue. Use GitHub's
[private vulnerability reporting](https://github.com/w9smz8qkh6-stack/safegloss-legacy/security/advisories/new)
and include the affected component, reproduction steps, impact, and any
suggested mitigation. Do not include live secrets; revoke or rotate them first.

## Deployment notes

- Set `DEBUG=False` in production.
- Provide a unique, randomly generated `SECRET_KEY`; production startup fails
  when it is absent.
- Restrict `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to the deployed domains.
- Use HTTPS and secure cookies. Enable HSTS only after HTTPS is verified for
  every applicable domain and subdomain.
- Keep credentials in the deployment platform's secret store, not in Git.
- Treat database exports, uploaded media, generated PDFs, and analytics data as
  sensitive and keep them outside the repository.
- Review authentication, authorization, retention, and consent requirements
  before processing student or research data.
