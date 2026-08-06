.PHONY: serve validate data checksums

serve:
	python3 -m http.server 8000

validate:
	python3 scripts/validate_repo.py
	node --check assets/js/markdown.js
	node --check assets/js/app.js
	node --check sw.js

data:
	python3 scripts/export_web_data.py

checksums:
	python3 scripts/make_checksums.py
