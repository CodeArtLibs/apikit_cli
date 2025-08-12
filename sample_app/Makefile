clear:
	clear

shell:
	docker run -v ./apps:/app/apps --network host -it apikit-dev:latest ash

help:
	@../env/bin/python ../apikit_cli/apikit.py --help
	@echo '--------------------------------------'

version:
	@../env/bin/python ../apikit_cli/apikit.py version
	@echo '--------------------------------------'

check:
	@../env/bin/python ../apikit_cli/apikit.py check
	@echo '--------------------------------------'

upgrade:
	@../env/bin/python ../apikit_cli/apikit.py upgrade
	@echo '--------------------------------------'

format:
	@../env/bin/python ../apikit_cli/apikit.py format
	@echo '--------------------------------------'

lint:
	@../env/bin/python ../apikit_cli/apikit.py lint
	@echo '--------------------------------------'

compile:
	@../env/bin/python ../apikit_cli/apikit.py compile
	@echo '--------------------------------------'

tests:
	@../env/bin/python ../apikit_cli/apikit.py tests
	@echo '--------------------------------------'

build:
	@../env/bin/python ../apikit_cli/apikit.py build
	@echo '--------------------------------------'

rebuild:
	@../env/bin/python ../apikit_cli/apikit.py rebuild
	@echo '--------------------------------------'

ci:
	@../env/bin/python ../apikit_cli/apikit.py ci
	@echo '--------------------------------------'

start:
	@../env/bin/python ../apikit_cli/apikit.py start
	@#../env/bin/python ../apikit_cli/apikit.py start --port 33334
	@echo '--------------------------------------'

stop:
	@../env/bin/python ../apikit_cli/apikit.py stop
	@echo '--------------------------------------'

ping:
	@../env/bin/python ../apikit_cli/apikit.py ping
	@echo '--------------------------------------'

create_admin:
	@../env/bin/python ../apikit_cli/apikit.py create_admin
	@echo '--------------------------------------'

db_changes:
	@../env/bin/python ../apikit_cli/apikit.py db_changes
	@echo '--------------------------------------'

db_migrate:
	@../env/bin/python ../apikit_cli/apikit.py db_migrate
	@echo '--------------------------------------'

db_clean:
	@../env/bin/python ../apikit_cli/apikit.py db_clean
	@echo '--------------------------------------'

update_dev:
	@../env/bin/python ../apikit_cli/apikit.py update_dev
	@echo '--------------------------------------'

create_alpha:
	@../env/bin/python ../apikit_cli/apikit.py create_alpha
	@echo '--------------------------------------'

admin:
	@../env/bin/python ../apikit_cli/apikit.py admin
	@echo '--------------------------------------'

python:
	@../env/bin/python ../apikit_cli/apikit.py python
	@echo '--------------------------------------'

report_bug:
	@../env/bin/python ../apikit_cli/apikit.py report_bug
	@echo '--------------------------------------'


test_env: clear help version check upgrade

test_ci: clear format lint compile tests build rebuild ci

test_dev: start stop db_migrate db_clean

test_cd: update_dev create_alpha

test_debug: admin python report_bug

test: test_env test_ci test_dev test_cd test_debug
