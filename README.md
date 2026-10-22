# DevJobHub

Get personalised programming job postings right to your telegram with ease [https://t.me/devjobhub](https://t.me/devjobhub)

## Runtime and dependencies

Use Python 3.11 and MongoDB 4.4 or newer (prefer a currently supported
MongoDB release). PyMongo 4.18.2 no longer supports older servers; check
the server version before deployment. No server upgrade or deployment is
performed by installing these dependencies.

Install `bot/requirements.txt` in a virtual environment. The maintained
`python-telegram-bot` package supplies `telegram`; do not install the unrelated
`telegram` package into the same environment.

The Telegram callbacks use the asynchronous API in python-telegram-bot 22.8.
Handlers remain sequential, broadcasts retain a maximum of five concurrent
sends, and the scraper still processes sources in the original order.
The old framework bundled urllib3 and pinned an obsolete Tornado; upgrading
only the standalone HTTP packages would not have patched those copies.

Run the bot from `bot/` with `python devjobhub.py`; the scraper worker remains
`python devjobhub_cron.py`. Both require the existing private `config.json`.
Do not start either worker for validation: they contact Telegram, MongoDB,
and/or job sites. Syntax checking (`python -m compileall -q bot`) is safe.
Hosted validation uses synthetic Telegram updates and an isolated MongoDB
service, never production credentials.

Installer limitation (2026-10-22): current pip 26.2.2 still bundles urllib3
2.7.0, which has advisories fixed in 2.8.0. The application pin does not patch
pip's private copy. Hosted artifacts inventory these installation-tool copies;
the bot itself uses the maintained HTTPX transport. A newer patched installer
release is still needed; this is not a claim that every bundled tool is clean.
