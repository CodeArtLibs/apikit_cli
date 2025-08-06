"""
Script to be called during development/initialization/maintenance.
"""

from __future__ import annotations

import argparse
import time
import httpx
import uvloop
from api_web import main

from rich import print
import asyncio
import subprocess
import typing


from api_web import exceptions
from api_web.utils.log import Log


class ShellCmdOutput(typing.TypedDict):
    cmd: str
    code: str
    output: str
    error: bool
    elapsed_secs: float

# print("[bold red]Error:[/] Something went wrong")

class CommandCLI:
    def execute_shell_command(
        self,
        command_line: str,
        cwd: str = None,
        timeout_secs: int = 60,
        kill_timeout_secs: int = 2,
        raise_on_error: bool = False,
        env: dict | None = None,
        log_cmd: bool = True,
    ) -> ShellCmdOutput:
        process: asyncio.subprocess.Process | None = None

        try:
            ref: float = time.time()
            process = asyncio.create_subprocess_shell(
                command_line,
                cwd=cwd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            asyncio.wait_for(process.wait(), timeout=timeout_secs)
            stdout: bytes
            stderr: bytes
            stdout, stderr = process.communicate()
            elapsed_secs: float = round(time.time() - ref, 2)

            if log_cmd:
                # Don't log sensitive command lines
                Log.info(f"{command_line} => {process.returncode}", layer="shell")
            if stdout:
                Log.info(f"Output: {stdout.decode()}", layer="shell")
            if stderr:
                Log.warn(command_line, layer="shell")
                Log.warn(
                    f"Error {process.returncode}: {stderr.decode()}", layer="shell"
                )

            if process.returncode != 0:
                if raise_on_error:
                    raise exceptions.PyApiServerError(
                        "Shell error",
                        cmd=command_line,
                        shell_code=process.returncode,
                        shell_output=stdout,
                        shell_error=stderr,
                    )

            # Log.vars(cmd=command_line, code=process.returncode, output=stdout or stderr)
            return {
                "cmd": command_line,
                "code": str(process.returncode),
                "output": (stdout or stderr).decode(),
                "error": process.returncode != 0,
                "elapsed_secs": elapsed_secs,
            }
        except (TimeoutError, subprocess.TimeoutExpired) as e:
            raise exceptions.PyApiServerError("Shell timeout", cmd=command_line) from e
        except subprocess.CalledProcessError as e:
            raise exceptions.PyApiServerError(
                "Shell timeout", cmd=command_line, code=e.returncode, error=e.stderr
            ) from e
        except Exception as e:
            raise exceptions.PyApiServerError(
                "Unknown shell error",
                cmd=command_line,
                exception=type(e).__name__,
                error=str(e),
                cwd=cwd,
            ) from e
        finally:
            if process:
                rc: int | None = process.returncode
                if rc is None:
                    try:
                        process.terminate()  # SIGTERM
                        time.sleep(
                            kill_timeout_secs
                        )  # Give some time to terminate the process
                        if rc is None:
                            process.kill()  # SIGKILL
                    except Exception as e:
                        # ignore for now, for mypyc
                        Log.warn(str(e), layer="shell")

    def execute():
        pass


class CheckEnvCommandCLI(CommandCLI):
    def execute():
        pass


class UpgradeCommandCLI(CommandCLI):
    def execute():
        # pip
        pass

    def check_for_update(current_version):
        r = httpx.get(
            "https://raw.githubusercontent.com/youruser/yourrepo/main/version.txt"
        )
        latest_version = r.text.strip()
        return latest_version if latest_version != current_version else None


class DepsCommandCLI(CommandCLI):
    def execute():
        # pip
        pass


class FormatCommandCLI(CommandCLI):
    def execute():
        # ruff
        pass


class LintCommandCLI(CommandCLI):
    def execute():
        # ruff
        # mypy
        pass


class CompileCommandCLI(CommandCLI):
    def execute():
        # pycompile
        # mypyc
        # cython
        pass


class BuildCommandCLI(CommandCLI):
    def execute():
        # docker build
        pass


class RunCommandCLI(CommandCLI):
    def execute():
        # docker compose up apikit
        # open localhost
        # uvicorn hot reload: uvicorn your_module:app --reload --reload-dir path/to/watch
        # docker compose volume
        pass


class AdminCommandCLI(CommandCLI):
    def execute():
        ADMIN_URL: str = "http://localhost:9001/auth/signin?"
        API_URL: str = "http://localhost:50000"
        f"open {ADMIN_URL}api={API_URL}"


COMMANDS = {
    "upgrade": UpgradeCommandCLI(),
    "check_env": CheckEnvCommandCLI(),
    "deps": DepsCommandCLI(),
    "format": FormatCommandCLI(),
    "lint": LintCommandCLI(),
    "compile": CompileCommandCLI(),
    "build": BuildCommandCLI(),
    "run": RunCommandCLI(),
    "admin": AdminCommandCLI(),
}


async def script(command: str, args: list[str]) -> None:
    from api_web.docs import (
        App,  # type: ignore[attr-defined]
    )

    app: App = App.manager.get_by_or_raise(app=args.app)
    if command == "manager_setup":
        # Equals to APIKit Setup
        # Request to App's API. In case of APIManager, it will make a request to itself.
        app.call_setup(args.email, args.password)
        # DatabaseSchemaUpdate.manager.migrate()
        # User.manager.create_first_user(email=args.email, password=args.password)
        # DatabaseSchemaUpdate.manager.load_data(reset_defaults=args.reset_defaults, extra_data=False)
        # APIManager Setup
        app.get_first_version()
        app.get_dev_version(args.email)
    elif command == "branch_summary":
        pass
        # ci: CI = CI(app, branch=args.branch or 'main', commit=args.commit, trigger='command_branch_summary')
        # try:
        #     return ci.branch_summary()
        # finally:
        #     ci.terminate()


if __name__ == "__main__":
    """
    source .env
    Usage:
    docker compose run api_manager_api_0 ash
    env/bin/python manager_commands.py manager_setup --app app --email ... --password ... --reset_defaults
    env/bin/python manager_commands.py branch_summary --app app --branch main
    """

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    cmd_setup = subparsers.add_parser("deps")
    cmd_setup.add_argument("--app", required=True)
    cmd_setup.add_argument("--reset_defaults", action="store_true", default=False)

    cmd_setup = subparsers.add_parser("lint")
    cmd_setup.add_argument("--app", required=True)
    cmd_setup.add_argument("--branch", default="main")

    cmd_setup = subparsers.add_parser("format")
    cmd_setup = subparsers.add_parser("compile")
    cmd_setup = subparsers.add_parser("deps")

    args = parser.parse_args()

    main.initialize()  # Load api_web.docs
    uvloop.run(script(args.command, args))
