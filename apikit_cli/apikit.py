"""
Script to be called during development/initialization/maintenance.
"""

from __future__ import annotations

import argparse
import configparser
import getpass
import os
import random
import secrets
import shlex
import shutil
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import time
import typing
import urllib.request
from contextlib import contextmanager

from packaging import version

API_KIT_VERSION = __version__ = '0.2'
DEBUG: bool = False


def color(color: str, string: str) -> str:
    return f'\033[1;{color}m{string}\033[0m'


def white(string: str) -> str:
    return color('37', string)


def green(string: str) -> str:
    return color('92', string)


def yellow(string: str) -> str:
    return color('33', string)


def red(string: str) -> str:
    return color('91', string)


def blue(string: str) -> str:
    return color('94', string)


def cyan(string: str) -> str:
    return color('36', string)


def random_suffix(length: int = 8) -> str:
    return secrets.token_hex(length // 2)


def find_repo_root(start_path: str | None = None) -> str | None:
    # basename $(git rev-parse --show-toplevel)
    if start_path is None:
        start_path = os.getcwd()
    current = start_path
    while current != os.path.dirname(current):  # until root
        if os.path.isdir(os.path.join(current, '.git')):
            return os.path.basename(current)
        current = os.path.dirname(current)
    return None


def find_free_port(start: int = 33200, end: int = 33299, shuffle: bool = False) -> int:
    ports = list(range(start, end + 1))
    if shuffle:
        random.shuffle(ports)
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    # fallback: ask OS for a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return int(s.getsockname()[1])


def get_app_config() -> dict[str, typing.Any]:
    """
    apikit.ini
    [apikit]
    app = myapp
    port = 33333
    api_url = http://localhost:33333
    admin_url = http://localhost:9001/auth/signin?api=http://localhost:33333')
    autoupdate = false
    report = false
    """
    config: dict[str, typing.Any]
    parser = configparser.ConfigParser()
    try:
        # CWD/apikit.ini
        parser.read('apikit.ini')
        config = dict(parser['apikit'])
    except Exception as e:
        print(red(str(e)))
        config = {}
    config.setdefault('app', find_repo_root())
    app: str = config['app']
    config.setdefault('port', '33333')
    config.setdefault('docker_image', f'{app}:dev')
    config.setdefault('token', '')
    config.setdefault('autoupdate', '1')
    config.setdefault('api_url', f'http://localhost:{config["port"]}')
    config.setdefault('admin_url', f'http://localhost:9001/auth/signin?api={config["api_url"]}')
    config.setdefault('autoupdate', '1')
    if DEBUG:
        print(white(str(config)))
    return config


def save_config() -> None:
    parser = configparser.ConfigParser()
    parser['apikit'] = CONFIG
    with open('apikit.ini', 'w') as f:
        parser.write(f)


CONFIG: dict[str, typing.Any] = get_app_config()


class APIKitCLIException(Exception):
    def __init__(self, msg: str, **kwargs: typing.Any) -> None:
        pass


class ShellCmdOutput(typing.TypedDict):
    cmd: str
    code: str
    output: str
    error: bool
    elapsed_secs: float


class CommandCLI:
    def __init__(self, **kwargs: typing.Any) -> None:
        print(kwargs)
        self.cli_args: dict[str, typing.Any] = kwargs or {}


    def execute_shell_command(
        self,
        command_line: str | list[str],
        *,
        cwd: str | None = None,
        raise_on_error: bool = False,
        capture_output: bool = False,
        timeout_secs: int = 30,
        env: dict[str, str] | None = None,
        kill_timeout_secs: int = 2,
    ) -> ShellCmdOutput:
        """
        e.g.: execute_shell_command('ls -la')
        :timeout in seconds
        """
        try:
            ref: float = time.time()
            result = subprocess.run(
                shlex.split(command_line) if isinstance(command_line, str) else command_line,
                cwd=cwd,
                shell=False,
                check=False,
                capture_output=capture_output,
                text=True,
                timeout=timeout_secs if capture_output else None,
                env=env,
            )
            elapsed_secs: float = round(time.time() - ref, 2)
            if DEBUG:
                print(f'{command_line} => {result.returncode}')  # , layer='shell')
            # if result.stdout:
            #     print(f'Output: {result.stdout}')  # , layer='shell')
            # if result.stderr:
            #     print(f'Error: {result.stderr}')  # , layer='shell')
            if result.returncode != 0:
                if raise_on_error:
                    raise APIKitCLIException(
                        'Shell error',
                        cmd=command_line,
                        shell_code=result.returncode,
                        shell_output=result.stdout,
                        shell_error=result.stderr,
                    )
            return {
                'cmd': command_line if isinstance(command_line, str) else ' '.join(command_line),
                'code': str(result.returncode),
                'output': result.stdout or result.stderr,
                'error': result.returncode != 0,
                'elapsed_secs': elapsed_secs,
            }
        except (TimeoutError, subprocess.TimeoutExpired) as e:
            raise APIKitCLIException('Shell timeout', cmd=command_line) from e
        except subprocess.CalledProcessError as e:
            raise APIKitCLIException('Shell timeout', cmd=command_line, code=e.returncode, error=e.stderr) from e
        except Exception as e:
            raise APIKitCLIException(
                'Unknown shell error',
                cmd=command_line,
                exception=type(e).__name__,
                error=str(e),
                cwd=cwd,
            ) from e
        # finally:
        #     if result:
        #         rc: int | None = result.returncode
        #         if rc is None:
        #             try:
        #                 result.terminate()  # SIGTERM
        #                 time.sleep(kill_timeout_secs )  # Give some time to terminate the process
        #                 if rc is None:
        #                     result.kill()  # SIGKILL
        #             except Exception as e:
        #                 # ignore for now, for mypyc
        #                 print(str(e), layer='shell')

    def docker_run(
        self,
        container_cmd: str,
        interactive: bool = False,
        capture_output: bool = False,
        detached: bool = False,
        port_mapping: str = '',
        host_network: bool = False,
        container_name: str = '',
        **env: str,
    ) -> None:
        # -p HOST_PORT:CONTAINER_PORT
        docker_image: str = CONFIG['docker_image']
        host_cmd: str
        env_vars: str = ' '.join([arg for k, v in env.items() for arg in ('-e', f'{k}={v}')])
        network: str = '--network host' if host_network else '--add-host=host.docker.internal:host-gateway'
        detached_attr: str = '-d' if detached else ''
        name: str = f'--name {container_name}' if container_name else ''
        if interactive:
            #
            host_cmd = (
                f'docker run {detached_attr} {name} -v ./apps:/app/apps {env_vars} {network} {port_mapping} -it {docker_image}'
            )
        else:
            host_cmd = f'docker run {detached_attr} {name} -v ./apps:/app/apps {env_vars} {network} {port_mapping} {docker_image}'
        if DEBUG:
            print(yellow(f'{host_cmd} {container_cmd}'))
        self.execute_shell_command(f'{host_cmd} {container_cmd}', capture_output=capture_output)

    def api_request(self, path: str, method: str = 'POST', **headers: str) -> None:
        self.execute_shell_command(f'http --verify=no --follow POST {CONFIG["api_url"]}{path}')

    def run_mongodb(self, container_name: str, storage_folder: str = '', network_host: bool = False) -> str:
        """
        docker start container_name
        docker stop container_name
        """

        port: int = find_free_port(shuffle=True)
        storage: str = f'-v {storage_folder}:/data/db' if storage_folder else ''
        cmd: str = f'docker run -d {storage} -p {port}:27017 --name {container_name} mongo:8.0.4-noble mongod --bind_ip_all'
        self.execute_shell_command(cmd, capture_output=True)
        self.cache_running_containers(container_name)
        # ?authSource=admin'
        if network_host:
            return 'mongodb://localhost:27017'
        else:
            return f'mongodb://host.docker.internal:{port}'

    def run_redis(self, container_name: str, network_host: bool = False) -> str:
        """
        docker start container_name
        docker stop container_name
        """

        port: int = find_free_port(shuffle=True)
        cmd: str = f'docker run -d -p {port}:6379 --name {container_name} redis:8.0-M02-alpine3.20'
        self.execute_shell_command(cmd, capture_output=True)
        self.cache_running_containers(container_name)
        if network_host:
            return 'redis://localhost:6379/0'
        else:
            return f'redis://host.docker.internal:{port}/0'

    def stop_docker_container(self, container_name: str) -> None:
        # stop => kill
        self.execute_shell_command(f'docker stop -t 3 {container_name}', capture_output=True)

    @contextmanager
    def with_mongodb(self, container_name: str, storage_folder: str = '') -> typing.Generator[str]:
        try:
            yield self.run_mongodb(container_name, storage_folder)
        finally:
            self.stop_docker_container(container_name)

    @contextmanager
    def with_redis(self, container_name: str) -> typing.Generator[str]:
        try:
            yield self.run_redis(container_name)
        finally:
            self.stop_docker_container(container_name)

    def get_cache_file(self) -> str:
        temp_dir: str = tempfile.gettempdir()
        return os.path.join(temp_dir, f'.apikit_{CONFIG["app"]}_cache')

    def cache_running_containers(self, container_name: str) -> None:
        with open(self.get_cache_file(), 'a') as f:
            f.write(f',{container_name}')

    def get_running_containers(self) -> list[str]:
        try:
            with open(self.get_cache_file(), 'r') as f:
                return f.read().split(',')
        except Exception:
            return []

    def clean_running_containers(self) -> None:
        try:
            os.remove(self.get_cache_file())
        except Exception:
            pass

    def execute(self) -> None:
        pass


class CommandCLIComposite(CommandCLI):
    commands: typing.ClassVar[list[str]] = []

    def __init__(self, **kwargs: str) -> None:
        super().__init__(**kwargs)

    def execute(self) -> None:
        for ref in self.__class__.commands:
            CommandCLIClass: type[CommandCLI] = COMMANDS[ref]
            cmd: CommandCLI = CommandCLIClass()
            cmd.execute()


class VersionCommandCLI(CommandCLI):
    def execute(self) -> None:
        print(f'APIKit version {API_KIT_VERSION}')


class CheckCommandCLI(CommandCLI):
    def execute(self) -> None:
        output: ShellCmdOutput = self.execute_shell_command('docker --version')
        if output['error']:
            print(red('Docker not found or it is not running.'))
        print(green('Env is OK.'))


class UpgradeCommandCLI(CommandCLI):
    def execute(self) -> None:
        try:
            latest_version: str = self.latest_version()
            if version.parse(latest_version) > version.parse(API_KIT_VERSION):
                print(yellow(f'APIKit CLI is out to date. Current {API_KIT_VERSION}. Latest {latest_version}'))
                self.upgrade_apikit_cli()
            else:
                print(f'APIKit CLI is up to date. Current {API_KIT_VERSION} - Latest {latest_version}')
        except Exception as e:
            print(red(str(e)))
            print(yellow('Update check failed.'))

    def latest_version(self) -> str:
        url: str = 'https://raw.githubusercontent.com/CodeArtLibs/apikit_cli/refs/heads/main/releases/latest.txt'
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=context) as response:
            return str(response.read().decode('utf-8').strip())
        return API_KIT_VERSION

    def upgrade_apikit_cli(self) -> None:
        try:
            url: str = 'https://raw.githubusercontent.com/CodeArtLibs/apikit_cli/refs/heads/main/apikit'
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(url, context=context) as response:
                data = response.read()
                with open('apikit_new', 'wb') as f:
                    f.write(data)
                # Downloading from GitHub it lost its executable permission
                os.chmod('apikit_new', os.stat('apikit_new').st_mode | stat.S_IEXEC)
            shutil.copy('apikit', 'apikit_old')
            shutil.copy('apikit_new', 'apikit')
            os.remove('apikit_new')
            print(green('Updated. Restarting...'))
            os.execv(sys.executable, [sys.executable, *sys.argv])
        except Exception as e:
            print(red(str(e)))
            print(yellow('Updated check failed'))


class FormatCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.docker_run('env/bin/ruff format /app/apps')


class LintCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.docker_run('env/bin/ruff check /app/apps --fix')
        self.docker_run('env/bin/python -OO -m compileall --workers 10 -q /app/apps')


class CompileCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.docker_run('env/bin/mypy /app/apps --strict --exclude "env/|tests"')


class TestsCommandCLI(CommandCLI):
    def execute(self) -> None:
        app: str = CONFIG['app']
        mongodb_container_name: str = f'{CONFIG["app"]}_tests_mongodb_{random_suffix()}'
        redis_container_name: str = f'{CONFIG["app"]}_tests_redis_{random_suffix()}'
        mongodb_url: str
        redis_url: str
        with self.with_mongodb(mongodb_container_name) as mongodb_url, self.with_redis(redis_container_name) as redis_url:
            pytest_cmd: str = '/app/env/bin/pytest --asyncio-mode=auto /app/apps -n auto -q --disable-warnings --tb=no'
            self.docker_run(
                pytest_cmd,
                host_network=False,
                DEV_ENV='true',
                TEST_ENV='true',
                MONGODB_URI=mongodb_url,
                MONGODB_NAME=f'{app}_unittest',
                REDIS_URL=redis_url,
            )


class BuildCommandCLI(CommandCLI):
    def execute(self) -> None:
        docker_image: str = CONFIG['docker_image']
        self.execute_shell_command(f'docker build -f Dockerfile . -t {docker_image}')
        # self.execute_shell_command(f'docker compose build --no-cache api_web')


class RebuildCommandCLI(CommandCLI):
    def execute(self) -> None:
        docker_image: str = CONFIG['docker_image']
        self.execute_shell_command(f'docker build --no-cache -f Dockerfile . -t {docker_image}')
        # self.execute_shell_command(f'docker compose rm api_web')
        # self.execute_shell_command(f'docker compose build --no-cache api_web')


class CICommandCLI(CommandCLIComposite):
    commands: typing.ClassVar[list[str]] = ['format', 'lint', 'compile', 'build', 'tests']


class StartCommandCLI(CommandCLI):
    def execute(self) -> None:
        app: str = CONFIG['app']
        mongodb_container_name: str = f'{CONFIG["app"]}_dev_mongodb_{random_suffix()}'
        redis_container_name: str = f'{CONFIG["app"]}_dev_redis_{random_suffix()}'
        mongodb_url: str
        redis_url: str
        with self.with_mongodb(mongodb_container_name, '.db') as mongodb_url, self.with_redis(redis_container_name) as redis_url:
            api_container_name: str = f'{CONFIG["app"]}_api_{random_suffix()}'
            self.cache_running_containers(api_container_name)

            port: str = str(self.cli_args.get('port', ''))
            if not port:
                port = str(find_free_port(start=int(CONFIG['port']), shuffle=False))
            CONFIG['port'] = port
            CONFIG['api_url'] = f'http://localhost:{port}'
            CONFIG['admin_url'] = f'http://localhost:9001/auth/signin?api={CONFIG["api_url"]}'
            CONFIG['mongodb_url'] = mongodb_url
            CONFIG['mongodb_db'] = f'{app}_dev'
            CONFIG['redis_url'] = redis_url
            CONFIG['token'] = secrets.token_hex(64)
            print(yellow('API: ') + CONFIG['api_url'])
            print(yellow('ADMIN: ') + CONFIG['admin_url'])
            save_config()
            self.docker_run(
                (
                    '/app/env/bin/uvicorn'
                    ' api_web.version_server:asgi_app'
                    ' --host 0.0.0.0'
                    f' --port {port}'
                    ' --workers 1'
                    ' --loop uvloop'
                    ' --interface asgi3'
                    ' --lifespan on'
                    ' --no-server-header'
                    ' --no-date-header'
                    ' --reload'
                    ' --reload-dir ./apps'
                ),
                port_mapping=f'-p {port}:{port}',
                host_network=False,
                container_name=api_container_name,
                DEV_ENV='true',
                API_VERSION='dev',
                MONGODB_URI=mongodb_url,
                MONGODB_NAME=f'{app}_dev',
                REDIS_URL=redis_url,
                APIKIT_SECRET_KEY=CONFIG['token'],
            )

        # docker_image: str = CONFIG['docker_image']
        # self.execute_shell_command(f'docker build -f Dockerfile . -t {docker_image}')
        # self.execute_shell_command('docker compose up -d')
        # self.execute_shell_command('docker compose logs -f api_web')


class StopCommandCLI(CommandCLI):
    def execute(self) -> None:
        for container in self.get_running_containers():
            self.stop_docker_container(container)
        self.clean_running_containers()


class CreateAdminCommandCLI(CommandCLI):
    def execute(self) -> None:
        # self.api_request('/data/SchemaChecking', itoken=CONFIG['token'])
        email: str = input("Enter admin's email: ")
        password: str = getpass.getpass("Enter admin's password: ")

        if 'mongodb_url' not in CONFIG:
            print(yellow('Start the API first: apikit start'))
            return
        cmd: str = f'/app/env/bin/python commands.py create_admin --email {email} --password {password}'
        self.docker_run(
            cmd,
            MONGODB_URI=CONFIG['mongodb_url'],
            MONGODB_NAME=CONFIG['mongodb_db'],
            REDIS_URL=CONFIG['redis_url'],
            API_VERSION='dev',
        )


class DBChangesCommandCLI(CommandCLI):
    def execute(self) -> None:
        # self.api_request('/data/SchemaChecking', itoken=CONFIG['token'])
        if 'mongodb_url' not in CONFIG:
            print(yellow('Start the API first: apikit start'))
            return
        cmd: str = '/app/env/bin/python commands.py db_changes'
        self.docker_run(
            cmd,
            MONGODB_URI=CONFIG['mongodb_url'],
            MONGODB_NAME=CONFIG['mongodb_db'],
            REDIS_URL=CONFIG['redis_url'],
            API_VERSION='dev',
        )


class DBMigrateCommandCLI(CommandCLI):
    def execute(self) -> None:
        # self.api_request('/data/updatedatabaseschema', itoken=CONFIG['token'])
        if 'mongodb_url' not in CONFIG:
            print(yellow('Start the API first: apikit start'))
            return
        cmd: str = '/app/env/bin/python commands.py db_migrate'
        self.docker_run(
            cmd,
            MONGODB_URI=CONFIG['mongodb_url'],
            MONGODB_NAME=CONFIG['mongodb_db'],
            REDIS_URL=CONFIG['redis_url'],
            API_VERSION='dev',
        )


class DBCleanCommandCLI(CommandCLI):
    def execute(self) -> None:
        if 'mongodb_url' not in CONFIG:
            print(yellow('Start the API first: apikit start'))
            return
        mongodb_url: str = CONFIG['mongodb_url']
        mongodb_db: str = CONFIG['mongodb_db']
        cmd = (
            f'env/bin/python -c '
            "'"
            'from pymongo import MongoClient; '
            f"""MongoClient("{mongodb_url}").drop_database("{mongodb_db}")"""
            "'"
        )
        self.docker_run(cmd)


class UpdateDevCommandCLI(CommandCLI):
    def execute(self) -> None:
        # Hints: git remote show origin ; git checkout dev ; git push origin dev
        print(yellow('git push to `dev` branch'))


class CreateAlphaCommandCLI(CommandCLI):
    def execute(self) -> None:
        # Hints: git remote show origin ; git checkout alpha ; git push origin alpha
        print(yellow('git push to `alpha` branch'))


class AdminCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command(f'open {CONFIG["admin_url"]}')


class PingCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.api_request('/status/ping')


class PythonCommandCLI(CommandCLI):
    def execute(self) -> None:
        # FIXME: use App's image
        self.docker_run('env/bin/python', interactive=True)


class ReportBugCommandCLI(CommandCLI):
    def execute(self) -> None:
        # TODO: request
        print(yellow('Noted, it will be investigated.'))


COMMANDS: dict[str, type[CommandCLI]] = {
    # Env
    'version': VersionCommandCLI,
    'check': CheckCommandCLI,
    'upgrade': UpgradeCommandCLI,
    # CI
    'format': FormatCommandCLI,
    'lint': LintCommandCLI,
    'compile': CompileCommandCLI,
    'tests': TestsCommandCLI,
    'build': BuildCommandCLI,
    'rebuild': RebuildCommandCLI,
    'ci': CICommandCLI,
    # Dev
    'start': StartCommandCLI,
    'stop': StopCommandCLI,
    'ping': PingCommandCLI,
    'create_admin': CreateAdminCommandCLI,
    'db_changes': DBChangesCommandCLI,
    'db_migrate': DBMigrateCommandCLI,
    'db_clean': DBCleanCommandCLI,
    # CD
    'update_dev': UpdateDevCommandCLI,
    'create_alpha': CreateAlphaCommandCLI,
    # Debug
    'admin': AdminCommandCLI,
    'python': PythonCommandCLI,
    'report_bug': ReportBugCommandCLI,
}


if __name__ == '__main__':
    """
    Usage:
    env/bin/python apikit_cli/apikit.py --help
    apikit --help
    apikit start --port 33333
    """

    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(dest='command', required=True)

    cli_parser: argparse.ArgumentParser
    # Env
    cli_parser = subparsers.add_parser('version')
    cli_parser = subparsers.add_parser('check')
    cli_parser = subparsers.add_parser('upgrade')
    # CI
    cli_parser = subparsers.add_parser('format')
    cli_parser = subparsers.add_parser('lint')
    cli_parser = subparsers.add_parser('compile')
    cli_parser = subparsers.add_parser('tests')
    cli_parser = subparsers.add_parser('build')
    cli_parser = subparsers.add_parser('rebuild')
    cli_parser = subparsers.add_parser('ci')
    # Dev
    cli_parser = subparsers.add_parser('start')
    cli_parser.add_argument('--port', type=int, required=False, default=33333)
    cli_parser = subparsers.add_parser('stop')
    cli_parser = subparsers.add_parser('ping')
    cli_parser = subparsers.add_parser('create_admin')
    cli_parser = subparsers.add_parser('db_changes')
    cli_parser = subparsers.add_parser('db_migrate')
    cli_parser = subparsers.add_parser('db_clean')
    # CD
    cli_parser = subparsers.add_parser('update_dev')
    cli_parser = subparsers.add_parser('create_alpha')
    # Debug
    cli_parser = subparsers.add_parser('admin')
    cli_parser = subparsers.add_parser('python')
    cli_parser = subparsers.add_parser('report_bug')

    args: argparse.Namespace = parser.parse_args()

    CommandCLIClass: type[CommandCLI] = COMMANDS[args.command]
    cmd: CommandCLI = CommandCLIClass(**vars(args))
    try:
        cmd.execute()
    except KeyboardInterrupt:
        pass
