clear:
	clear

clean: clear
	@rm -rf __pycache__ *.egg *.egg-info/ *.log
	@find . | grep -E "(/__pycache__$$|\.pyc$$|\.pyo$$)" | xargs rm -rf

prepare: clear
	python3 -m venv env

deps: clear
	env/bin/pip install --upgrade pip
	env/bin/pip install -r requirements.txt
	env/bin/pip install -r requirements-dev.txt

freeze: clear
	env/bin/pip freeze

shell: clear
	#source .env && PYTHONPATH="$$PYTHONPATH:."
	env/bin/python

format: clear
	env/bin/ruff format .

lint: clear
	@# env/bin/pre-commit run --all-files
	env/bin/ruff format .
	env/bin/ruff check . --fix
	-env/bin/python -OO -m compileall --workers 10 -q .
	env/bin/mypy . --strict

rebuild: clear
	docker compose -f docker-compose.yml build api_web --no-cache ; docker images

run: clear
	docker compose -f docker-compose.yml build api_web ; \
	docker compose -f docker-compose.yml up api_web

test_apikit: clear mypyc_clean cython_clean
	@printf "\033[34mTESTING APIKIT =============================================\033[0m\n"
	#time env/bin/python -m doctest api_web/*.py api_web/**/*.py -o FAIL_FAST # --verbose
	#time env/bin/python -m unittest discover --failfast
	#env/bin/pytest --cache-clear
	#rm -rf .pytest_cache
	time env/bin/pytest pydict api_web document --failed-first --last-failed -n auto

test_apikit_mypyc: clear mypyc_clean cython_clean mypyc_build test_apikit mypyc_clean cython_clean

test_apikit_cython: clear mypyc_clean cython_clean cython_build test_apikit mypyc_clean cython_clean

test: testpydict test_apikit

# Experimental

# 	MODULE="document/*.py" ;
check_module: clear
	MODULE="api_web/drivers/motor_driver.py" ; \
	env/bin/ruff format $$MODULE && \
	env/bin/ruff check $$MODULE --fix && \
	env/bin/python -OO -m compileall --workers 10 -q $$MODULE && \
	env/bin/mypy $$MODULE --strict \
		--html-report .report/mypy/specific \
		--any-exprs-report .report/mypy/specific \
		--lineprecision-report .report/mypy/specific && \
	env/bin/mypyc $$MODULE --install-types --follow-imports=normal --check-untyped-defs && \
	open -a "Google Chrome" .report/mypy/specific/index.html && \
	open -a "Google Chrome" .report/mypy/specific/lineprecision.txt && \
	open -a "Google Chrome" .report/mypy/specific/any-exprs.txt && \
	open -a "Google Chrome" .report/mypy/specific/types-of-anys.txt
	MODULE="api_web/drivers/motor_driver.py" ; \
	env/bin/cython -a $$MODULE && \
	open -a "Google Chrome" $$MODULE.html

mypy_apikit: clear
	-env/bin/mypy api_web/*.py api_web/utils/*.py api_web/drivers/*.py document/*.py \
		--config-file mypy.ini \
		--html-report .report/mypy/api_kit \
		--any-exprs-report .report/mypy/api_kit \
		--lineprecision-report .report/mypy/api_kit
	open .report/mypy/api_kit/index.html
	open -a "Google Chrome" .report/mypy/api_kit/lineprecision.txt
	open -a "Google Chrome" .report/mypy/api_kit/any-exprs.txt
	open -a "Google Chrome" .report/mypy/api_kit/types-of-anys.txt

mypyc_clean: clear
	# Clean previously generated .so libraries
	@find . -path "./env" -name "*.so*" -delete
	@find . -path "./env" -prune -o -name "*.so*" -type f -exec rm {} +
	# Clean previously generated C files
	@rm -rf .mypy_cache
	@rm -rf build/ *.c

mypyc_build: clear mypyc_clean cython_clean
	# Dev steps: 1. edit mypyc_setup.py, 2. make mypyc_build, 3. env/bin/python and test
	# env/bin/pip install setuptools --upgrade
	time env/bin/python mypyc_setup.py build_ext --inplace
	# env/bin/mypyc $$FILES --install-types --follow-imports=normal --check-untyped-defs
	# Clean generated intermediated files (C files)
	rm -rf build/ *.c

cython_clean:
	rm -rf cython_build/ *.c

cython_build: clear cython_clean mypyc_clean
	# Dev steps: 1. edit cython_setup.py, 2. make cython_build, 3. env/bin/python and test
	# env/bin/pip install setuptools --upgrade
	time env/bin/python cython_setup.py build_ext --inplace
	# Clean generated intermediated files (C files)
	rm -rf build/ *.c
