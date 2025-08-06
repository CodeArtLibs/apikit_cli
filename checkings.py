import pathlib


class DockerfileCheckingStep:
    def _execute(self) -> tuple[bool, str]:
        # os.path.join(self.project_dir, 'Dockerfile')
        # https://github.com/aquasecurity/trivy
        # https://github.com/anchore/grype
        # Block dangerous instructions:
        #   • ADD http://...
        #   • RUN curl | sh
        #   • RUN chmod 777 /
        #   • VOLUME / (can hide data)
        # with open('Dockerfile') as f:
        #     for line in f:
        #         if 'ADD http' in line or '| sh' in line:
        #             raise ValueError('Dangerous Dockerfile line')
        return (False, "")


class RequirementsCheckingStep:
    def _execute(self) -> tuple[bool, str]:
        # os.path.join(self.project_dir, 'requirements-app.txt')
        # pip-compile --dry-run --allow-unsafe
        # pipgrip -v -r requirements.txt
        # pip install -r requirements.txt
        # pip check
        # pip install req-lint
        # Run: req-lint requirements.txt
        return (False, "")


class PythonCheckingStep:
    def __init__(self, project_dir: str) -> None:
        super().__init__(optional=True)
        self.project_dir = project_dir

    def _execute(self) -> tuple[bool, str]:
        """
        Returns a list of the errors

        https://docs.python.org/3/library/security_warnings.html
        TODO: use IA to propose suggestions
        """

        # https://docs.python.org/3/library/functions.html
        dangerous_builtin_functions: list[str] = [
            "breakpoint",
            "compile",
            "delattr",
            "dir",
            "eval",
            "exec",
            "getattr",
            "globals",
            "hasattr",
            "help",
            "input",
            "locals",
            "open",
            "setattr",
            "__import__",
        ]

        # https://docs.python.org/3/library/index.html
        dangerous_modules: list[str] = [
            # File and Directory Access
            "pathlib",
            "os.path",
            "fileinput",
            "stat",
            "filecmp",
            "tempfile",
            "glob",
            "fnmatch",
            "linecache",
            "shutil",
            # Generic Operating System Services
            "os",
            "io",
            "argparse",
            "getopt",
            "logging",
            "logging.config",
            "logging.handlers",
            "getpass",
            "curses",
            "curses.textpad",
            "curses.ascii",
            "curses.panel",
            "platform",
            "errno",
            "ctypes",
            # Networking and Interprocess Communication
            "socket",
            "ssl",
            "select",
            "selectors",
            "signal",
            "mmap",
            # Development Tools
            "pydoc",
            "doctest",
            "unittest",
            "unittest.mock",
            "2to3",
            "test",
            "test.support",
            "test.support.socket_helper",
            "test.support.script_helper",
            "test.support.bytecode_helper",
            "test.support.threading_helper",
            "test.support.os_helper",
            "test.support.import_helper",
            "test.support.warnings_helper",
            # Debugging and Profiling
            "bdb",
            "faulthandler",
            "pdb",
            "The",
            "timeit",
            "trace",
            "tracemalloc",
            # Software Packaging and Distribution
            "ensurepip",
            "venv",
            "zipapp",
            # Python Runtime Services
            "sys",
            "sys.monitoring",
            "sysconfig",
            "builtins",
            "__main__",
            "warnings",
            "abc",
            "atexit",
            "traceback",
            "__future__",
            "gc",
            "inspect",
            "site",
            # Custom Python Interpreters
            "code",
            "codeop",
            # Importing Modules
            "zipimport",
            "pkgutil",
            "modulefinder",
            "runpy",
            "importlib",
            "importlib.resources",
            "importlib.resources.abc",
            "importlib.metadata",
            # Python Language Services
            "ast",
            "symtable",
            "token",
            "keyword",
            "tokenize",
            "tabnanny",
            "pyclbr",
            "py_compile",
            "compileall",
            "dis",
            "pickletools",
            # MS Windows Specific Services
            "msvcrt",
            "winreg",
            "winsound",
            # Unix Specific Services
            "posix",
            "pwd",
            "grp",
            "termios",
            "tty",
            "pty",
            "fcntl",
            "resource",
            "syslog",
            # Modules command-line interface (CLI)
            "cgi",
            "cgitb",
            "chunk",
            "mailcap",
            "msilib",
            "nis",
            "nntplib",
            "optparse",
            "ossaudiodev",
            "pipes",
            "sndhdr",
            "spwd",
            "sunau",
            "telnetlib",
            "uu",
            "xdrlib",
        ]

        dangerous_reserved_words: list[str] = [
            "global",
            # '__',
            "__dict__",
        ]

        alerts: list[str] = []
        files: list[pathlib.Path] = list(pathlib.Path(self.project_dir).rglob("*.py"))
        for f in files:
            if "env" in f.parts:
                # Skip checking python libraries in virtual env
                continue
            if f.parent == pathlib.Path(self.project_dir) or f.name in (
                "mypyc_setup.py",
                "shell_start.py",
            ):
                # Skip root files like mypyc_setup.py, shell_start.py etc
                continue
            with open(f, "r") as fd:
                code: str = fd.read()
                for i, line in enumerate(code.split("\n"), start=1):
                    if line.strip().startswith("#"):
                        continue  # skip comments
                    elif line.strip() == "from __future__ import annotations":
                        continue

                    # ignore comment lines (not strings)
                    for func in dangerous_builtin_functions:
                        if func in line:
                            alerts.append(f"- Line {i}: {func} - {line}")

                    # check line per line, check if the word is in the line, check for from/import
                    for mod in dangerous_modules:
                        if f"import {mod}" in line:
                            alerts.append(f"* Line {i}: {mod} - {line}")

                    for word in dangerous_reserved_words:
                        if word in line:
                            alerts.append(f"> Line {i}: {word} - {line}")

                    # 3rd_party_libs
        return (bool(alerts), "; ".join(alerts))
