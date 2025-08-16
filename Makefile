CLI_VERSION := 0.0

# -------------------------------------------------------------------------------------------------
# CLI Development

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
	env/bin/ruff format . --exclude sample_app

lint: clear clean format
	@# env/bin/pre-commit run --all-files
	env/bin/ruff check . --fix --exclude sample_app
	-env/bin/python -OO -m compileall --workers 10 -q .
	env/bin/mypy . --strict --exclude 'env/|tests|sample_app/'
	# --ignore-missing-imports

# -------------------------------------------------------------------------------------------------
# APIKit CLI Build

test: clear
	time env/bin/pytest . -n auto --ignore sample_app
	#time env/bin/pytest . --failed-first --last-failed -n auto
	# Env
	env/bin/python apikit_cli/apikit.py --help
	env/bin/python apikit_cli/apikit.py version
	env/bin/python apikit_cli/apikit.py check
	env/bin/python apikit_cli/apikit.py upgrade
	# CI
	env/bin/python apikit_cli/apikit.py format
	env/bin/python apikit_cli/apikit.py lint
	env/bin/python apikit_cli/apikit.py compile
	env/bin/python apikit_cli/apikit.py tests
	env/bin/python apikit_cli/apikit.py build
	env/bin/python apikit_cli/apikit.py rebuild
	env/bin/python apikit_cli/apikit.py ci
	# Dev
	env/bin/python apikit_cli/apikit.py start
	env/bin/python apikit_cli/apikit.py stop
	env/bin/python apikit_cli/apikit.py ping
	env/bin/python apikit_cli/apikit.py create_admin
	env/bin/python apikit_cli/apikit.py db_changes
	env/bin/python apikit_cli/apikit.py db_migrate
	env/bin/python apikit_cli/apikit.py db_clean
	# CD
	env/bin/python apikit_cli/apikit.py update_dev
	env/bin/python apikit_cli/apikit.py create_alpha
	# Debug
	env/bin/python apikit_cli/apikit.py admin
	env/bin/python apikit_cli/apikit.py python
	env/bin/python apikit_cli/apikit.py report_bug

build: clear format lint
	# Slow startup
	#env/bin/pyinstaller --hidden-import=rich --onefile apikit_cli/apikit.py --distpath ./dist
	#env/bin/python -m nuitka --python-flag=no_asserts --python-flag=no_docstrings --python-flag=unbuffered --include-package=rich --standalone --onefile --show-progress --output-dir=./dist apikit_cli/apikit.py
	# Faster command startup. Depends on Python installed in the machine
	env/bin/python -m nuitka --python-flag=no_asserts --python-flag=no_docstrings --python-flag=unbuffered --show-progress --output-dir=./dist apikit_cli/apikit.py

test_bin: clear
	# Env
	apikit --help
	apikit version
	apikit check
	apikit upgrade
	# CI
	apikit format
	apikit lint
	apikit compile
	apikit tests
	apikit build
	apikit rebuild
	apikit ci
	# Dev
	apikit start
	apikit stop
	apikit ping
	apikit create_admin
	apikit db_changes
	apikit db_migrate
	apikit db_clean
	# CD
	apikit update_dev
	apikit create_alpha
	# Debug
	apikit admin
	apikit python
	apikit report_bug

update: build
	# Nuitka
	cp ./dist/apikit.bin apikit
	# PyInstaller
	#cp ./dist/apikit apikit
	rm releases/latest.txt
	echo $(CLI_VERSION) > releases/latest.txt

copy:
	cp apikit ../apikit_template

all: test build test_bin update copy

# Update Makefile/CLI_VERSION and apikit.py/API_KIT_VERSION
publish: copy
	echo $(CLI_VERSION) > releases/latest.txt
	shasum -a 256 apikit > releases/apikit_$(CLI_VERSION).hash
	git add releases/latest.txt releases/apikit_$(CLI_VERSION).hash apikit apikit_cli/apikit.py Makefile
	git commit -m "Release $(CLI_VERSION)"
	git push origin main
	git tag $(CLI_VERSION)
	git push origin $(CLI_VERSION)
	# Delete Git tag:
	# git tag -d 0.0 && git push origin :0.0


# -------------------------------------------------------------------------------------------------
# Act

act_install: clear
	brew install act

act_docker_image: clear
	docker pull catthehacker/ubuntu:act-latest
	#docker pull nektos/act

act_list: clear
	act --list

act_check: clear
	act --dryrun -W .github/workflows/build.yaml

act_build: clear
	# -e event.json
	act -W .github/workflows/build.yaml --job build

act_all: clear
	ACTIONS_STEP_DEBUG=false act --quiet
