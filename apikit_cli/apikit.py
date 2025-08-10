"""
Script to be called during development/initialization/maintenance.
"""

from __future__ import annotations

import argparse
import configparser
import os
import shutil
import ssl
import stat
import subprocess
import sys
import time
import typing
import urllib.request

from packaging import version

API_KIT_VERSION = __version__ = '0.1'


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
    def __init__(self, **kwargs: str) -> None:
        pass

    def execute_shell_command(
        self,
        command_line: str,
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
                command_line.split(),
                cwd=cwd,
                shell=False,
                check=False,
                capture_output=capture_output,
                text=True,
                timeout=timeout_secs if capture_output else None,
                env=env,
            )
            elapsed_secs: float = round(time.time() - ref, 2)
            # print(f'{command_line} => {result.returncode}')  # , layer='shell')
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
                'cmd': command_line,
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

    def docker_run(self, container_cmd: str, interactive: bool = False, capture_output: bool = False) -> None:
        # -p HOST_PORT:CONTAINER_PORT
        host_cmd: str
        if interactive:
            host_cmd = 'docker run -v ./apps:/app/apps --network host -it apikit-dev:latest'
        else:
            host_cmd = 'docker run -v ./apps:/app/apps --network host apikit-dev:latest'
        print(yellow(f'{host_cmd} {container_cmd}'))
        self.execute_shell_command(f'{host_cmd} {container_cmd}', capture_output=capture_output)

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
        # pip
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
        url: str = 'https://raw.githubusercontent.com/CodeArtLibs/apikit_cli/refs/heads/main/version.txt'
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
        pytest: str = """
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
asyncio_default_test_loop_scope = session
testpaths = apps
env =
    API_VERSION=test
    MONGODB_URI=mongodb://localhost:27017/{app}_test?authSource=admin
    MONGODB_NAME={app}_test
    REDIS_URL=redis://localhost:6379/0
    DEV_ENV=true
    TEST_ENV=true
"""
        pytest_cmd: str = (
            '/app/env/bin/pytest'
            ' --asyncio-mode=auto'
            # ' --asyncio-default-fixture-loop-scope=session'
            # ' --asyncio-default-test-loop-scope=session'
            # ' --env=API_VERSION=test'
            # ' --env=MONGODB_URI=mongodb://localhost:27017/apikit_unittest?authSource=admin'
            # ' --env=MONGODB_NAME=apikit_unittest'
            # ' --env=REDIS_URL=redis://localhost:6379/0'
            # ' --env=DEV_ENV=true'
            # ' --env=TEST_ENV=true'
            ' /app/apps -n auto -q --disable-warnings --tb=no'
        )
        self.docker_run(pytest_cmd)


class BuildCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command(f'docker compose build --no-cache apikit-{app}')


class RebuildCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command(f'docker compose rm {app}')
        self.execute_shell_command(f'docker compose build --no-cache {app}')


class CICommandCLI(CommandCLIComposite):
    commands: typing.ClassVar[list[str]] = ['format', 'lint', 'compile', 'build', 'tests']


class StartCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command('docker compose up -d')
        print(yellow('open http://localhost:50000'))
        self.execute_shell_command('open http://localhost:50000')
        self.execute_shell_command('docker compose logs -f api_web api_tasks')


class StopCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command('docker compose down --remove-orphans')


class DBMigrateCommandCLI(CommandCLI):
    def execute(self) -> None:
        pass
        # self.execute_shell_command('docker compose ')


class DBCleanCommandCLI(CommandCLI):
    def execute(self) -> None:
        pass
        # self.execute_shell_command('docker compose ')


class UpdateDevCommandCLI(CommandCLI):
    def execute(self) -> None:
        print(yellow('git push to `dev` branch'))


class CreateAlphaCommandCLI(CommandCLI):
    def execute(self) -> None:
        print(yellow('git push to `alpha` branch'))


class AdminCommandCLI(CommandCLI):
    def execute(self) -> None:
        ADMIN_URL: str = 'http://localhost:9001/auth/signin?'
        API_URL: str = 'http://localhost:50000'
        self.execute_shell_command(f'open {ADMIN_URL}api={API_URL}')


class PingCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command(f'http POST http://localhost:33333/status/ping')


class PythonCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.docker_run('env/bin/python', interactive=True)


class ReportBugCommandCLI(CommandCLI):
    def execute(self) -> None:
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


def read_config_file() -> None:
    """
    apikit.ini
    [apikit]
    app = localhost
    port = 33333
    autoupdate = false
    report = false
    """
    config = configparser.ConfigParser()
    try:
        config.read('config.ini')
        config['apikit']['port']
        config['apikit']['app']
    except Exception:
        pass


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
    cmd.execute()
