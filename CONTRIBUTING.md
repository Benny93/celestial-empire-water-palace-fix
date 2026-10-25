# Reporting and contributing

For a bug report, include the game build (if known), Python version, exact error,
whether the save predates updates, and what the UI showed before and after loading.
Distinguish a structural validation pass from resumed delivery and full completion.
Redact personal paths from terminal output. Do not attach private saves publicly
unless you deliberately intend to share the city and all its serialized data.

Keep fixes targeted. Do not introduce global string replacements, automatic live-save
installation, arbitrary completion flags, or changes to unrelated resource counts.
Add a synthetic regression test for any new supported state. Never commit game saves,
decompressed data, game assets, logs containing personal data, or generated reports.

Run `python -m unittest discover -s tests -v` before proposing changes.
