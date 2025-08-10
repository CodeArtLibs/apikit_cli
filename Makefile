CLI_VERSION := 0.0

clear:
	clear

clean: clear
	@rm -rf __pycache__ *.egg *.egg-info/ *.log
	@find . | grep -E "(/__pycache__$$|\.pyc$$|\.pyo$$)" | xargs rm -rf
	@rm -rf dist/*

prepare: clear
	python3 -m venv env

deps: clear
	env/bin/pip install --upgrade pip
	env/bin/pip install -r requirements.txt
	env/bin/pip install -r requirements-dev.txt
	# curl https://nuitka.net/ccache/v4.2.1/ccache-4.2.1.zip --output ccache-4.2.1.zip
	# mv ccache-4.2.1.zip /Users/paulocheque/Library/Caches/Nuitka/downloads/ccache/v4.2.1/ccache-4.2.1.zip

freeze: clear
	env/bin/pip freeze

shell: clear
	#source .env && PYTHONPATH="$$PYTHONPATH:."
	env/bin/python

format: clear
	env/bin/ruff format .

lint: clear clean format
	@# env/bin/pre-commit run --all-files
	env/bin/ruff format .
	env/bin/ruff check . --fix
	-env/bin/python -OO -m compileall --workers 10 -q .
	env/bin/mypy . --strict --exclude 'env/|tests'
	# --ignore-missing-imports

test: clear
	time env/bin/pytest . -n auto
	#time env/bin/pytest . --failed-first --last-failed -n auto
	env/bin/python apikit_cli/apikit.py --help
	env/bin/python apikit_cli/apikit.py version
	env/bin/python apikit_cli/apikit.py check_env
	env/bin/python apikit_cli/apikit.py upgrade
	env/bin/python apikit_cli/apikit.py format
	env/bin/python apikit_cli/apikit.py lint
	env/bin/python apikit_cli/apikit.py compile
	env/bin/python apikit_cli/apikit.py build
	env/bin/python apikit_cli/apikit.py run
	env/bin/python apikit_cli/apikit.py tests
	env/bin/python apikit_cli/apikit.py admin

build: clear format lint test
	env/bin/pyinstaller --hidden-import=rich --onefile apikit_cli/apikit.py --distpath ./dist
	env/bin/python -m nuitka --python-flag=no_asserts --python-flag=no_docstrings --python-flag=unbuffered --include-package=rich --standalone --onefile --show-progress --output-dir=./dist apikit_cli/apikit.py

test_bin: clear
	apikit --help
	apikit version
	apikit check_env
	apikit upgrade
	apikit format
	apikit lint
	apikit compile
	apikit build
	apikit run
	apikit tests
	apikit admin

publish: build
	# Nuitka
	cp ./dist/apikit.bin apikit
	# PyInstaller
	cp ./dist/apikit apikit
	rm version.txt
	echo $(CLI_VERSION) > version.txt

all: build test_bin publish
