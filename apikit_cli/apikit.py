"""
Script to be called during development/initialization/maintenance.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import typing
import urllib.request

from packaging import version
from rich.console import Console

console = Console()

API_KIT_VERSION = __version__ = '0.0'


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
                capture_output=True,
                text=True,
                timeout=timeout_secs,
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

    def execute(self) -> None:
        pass


class VersionCommandCLI(CommandCLI):
    def execute(self) -> None:
        print(f'APIKit version {API_KIT_VERSION}')


class CheckEnvCommandCLI(CommandCLI):
    def execute(self) -> None:
        output: ShellCmdOutput = self.execute_shell_command('docker --version')
        if output['error']:
            console.print('Docker not found or it is not running.', style='bold red')
        console.print('Env is OK.', style='bold green')


class UpgradeCommandCLI(CommandCLI):
    def execute(self) -> None:
        # pip
        try:
            latest_version: str = self.latest_version()
            if version.parse(latest_version) > version.parse(API_KIT_VERSION):
                self.upgrade_apikit_cli()
            else:
                print('APIKit CLI is up to date.')
        except Exception:
            console.print('Update check failed.', style='bold yellow')

    def latest_version(self) -> str:
        with console.status('Checking...'):
            url: str = 'https://raw.githubusercontent.com/codeartlib/apikit_cli/main/version.txt'
            with urllib.request.urlopen(url) as response:
                return str(response.read().decode('utf-8').strip())
            return API_KIT_VERSION

    def upgrade_apikit_cli(self) -> None:
        try:
            with console.status('Downloading...'):
                url: str = 'https://raw.githubusercontent.com/codeartlib/apikit_cli/main/apikit_cli'
                urllib.request.urlretrieve(url, 'apikit_cli_new')
            with console.status('Updating...'):
                shutil.copy('apikit_cli', 'apikit_cli_old')
                shutil.copy('apikit_cli_new', 'apikit_cli')
                os.remove('apikit_cli_new')
            console.print('Updated. Restarting...', style='bold green')
            os.execv(sys.executable, [sys.executable, *sys.argv])
        except Exception:
            console.print('Updated check failed', style='bold yellow')


# class DepsCommandCLI(CommandCLI):
#     def execute(self) -> None:
#         # pip
#         pass


class FormatCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command('docker compose run api_web env/bin/ruff format .')


class LintCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command('docker compose run api_web env/bin/ruff check . --fix')
        self.execute_shell_command('docker compose run api_web env/bin/python -OO -m compileall --workers 10 -q .')


class CompileCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command('docker compose run api_web env/bin/mypy . --strict --exclude "env/|tests"')


class BuildCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command('docker compose build --no-cache api_web')


class RebuildCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command('docker compose rm api_web')
        self.execute_shell_command('docker compose build --no-cache api_web')


class TestsCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command('docker compose run api_web env/bin/pytest . -n auto')


class RunCommandCLI(CommandCLI):
    def execute(self) -> None:
        self.execute_shell_command('docker compose up -d')
        console.print('open http://localhost:50000', style='bold yellow')
        self.execute_shell_command('open http://localhost:50000')
        self.execute_shell_command('docker compose logs -f api_web api_tasks')


class AdminCommandCLI(CommandCLI):
    def execute(self) -> None:
        ADMIN_URL: str = 'http://localhost:9001/auth/signin?'
        API_URL: str = 'http://localhost:50000'
        self.execute_shell_command(f'open {ADMIN_URL}api={API_URL}')


COMMANDS: dict[str, type[CommandCLI]] = {
    'version': VersionCommandCLI,
    'check_env': CheckEnvCommandCLI,
    'upgrade': UpgradeCommandCLI,
    # 'deps': DepsCommandCLI,
    'format': FormatCommandCLI,
    'lint': LintCommandCLI,
    'compile': CompileCommandCLI,
    'build': BuildCommandCLI,
    'rebuild': RebuildCommandCLI,
    'run': RunCommandCLI,
    'tests': TestsCommandCLI,
    'admin': AdminCommandCLI,
}


if __name__ == '__main__':
    """
    Usage:
    env/bin/python apikit_cli/apikit.py --help
    apikit --help
    """

    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(dest='command', required=True)

    cmd_setup: argparse.ArgumentParser
    cmd_setup = subparsers.add_parser('version')
    cmd_setup = subparsers.add_parser('check_env')
    cmd_setup = subparsers.add_parser('upgrade')

    cmd_setup = subparsers.add_parser('format')
    cmd_setup = subparsers.add_parser('lint')
    cmd_setup = subparsers.add_parser('compile')
    cmd_setup = subparsers.add_parser('build')
    cmd_setup = subparsers.add_parser('tests')
    cmd_setup = subparsers.add_parser('run')

    cmd_setup = subparsers.add_parser('admin')
    cmd_setup = subparsers.add_parser('console')

    # cmd_setup = subparsers.add_parser('deps')
    # cmd_setup.add_argument('--app', required=True)
    # cmd_setup.add_argument('--reset_defaults', action='store_true', default=False)

    # cmd_setup = subparsers.add_parser('lint')
    # cmd_setup.add_argument('--app', required=True)
    # cmd_setup.add_argument('--branch', default='main')

    args: argparse.Namespace = parser.parse_args()

    CommandCLIClass: type[CommandCLI] = COMMANDS[args.command]
    cmd: CommandCLI = CommandCLIClass(**vars(args))
    cmd.execute()
