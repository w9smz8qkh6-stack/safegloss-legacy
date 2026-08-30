# Security policy

## Project status

SafeGloss Legacy is a research reconstruction, not a supported production
service. Do not process real participant or institutional data without an
independent security, privacy, consent, retention, and research-governance
review.

Report vulnerabilities privately through [GitHub private vulnerability
reporting](https://github.com/w9smz8qkh6-stack/safegloss-legacy/security/advisories/new).
Do not include live secrets or personal data.

## Operational controls

- Copy `.env.example` to an untracked `.env` and replace all placeholders.
- Production `APP_KEY` must be a unique random value of at least 32 characters.
- Terminate TLS in front of Apache and verify the application sees HTTPS so its
  session cookie receives the `Secure` flag.
- Keep the web container read-only and MySQL off public interfaces; the provided
  Compose file follows those defaults.
- Back up and test restoration of the MySQL volume before a real replication.
- Treat user profiles, consent timestamps, events, scores, IP-adjacent server
  logs, and captured mail reports as sensitive research data.
- `MAIL_TRANSPORT=database` is the safe non-delivering default. Enabling `smtp`
  transmits participant/session information to `RESEARCH_REPORT_TO`; configure
  only an approved destination and secret store. The adapter requires TLS peer
  verification.
- Review account lifecycle, password policy, role provisioning, join-code
  distribution, retention, export, incident response, and participant withdrawal
  procedures before collecting data.

The application uses password hashing, prepared statements, CSRF tokens,
server-side sessions, output escaping, allowlisted rich HTML, role checks,
content-security and framing headers, semantic treatment storage, and
server-received timestamps. These controls reduce risk but do not substitute for
deployment review or an external security assessment.
