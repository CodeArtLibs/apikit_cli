def test_utilities():
    from apikit_cli import apikit

    assert apikit.color('', '')
    assert apikit.white('')
    assert apikit.green('')
    assert apikit.yellow('')
    assert apikit.red('')
    assert apikit.blue('')
    assert apikit.cyan('')
    assert len(apikit.random_suffix(length=10)) == 10
    assert apikit.get_platform_arch() == 'macos-arm64' or apikit.get_platform_arch() == 'linux_amd64'
    assert apikit.find_repo_root() == 'apikit_cli'
    assert apikit.find_free_port() >= 33200 and apikit.find_free_port() <= 33299
    assert not apikit.version_lower_than('0.0', '0.0')
    assert apikit.version_lower_than('0.0', '0.1')
    assert not apikit.version_lower_than('0.1', '0.0')


def test_config_file():
    from apikit_cli import apikit

    config = apikit.get_app_config()
    assert config['app'] == 'apikit_cli'
    assert config['port'] == '33333'
    assert config['docker_image'] == 'apikit_cli:dev'
    assert config['api_url'] == 'http://localhost:33333'
    assert config['admin_url'] == 'http://localhost:9001/auth/signin?api=http://localhost:33333'


def test_base_command():
    from apikit_cli.apikit import CommandCLI, CommandCLIComposite

    cmd = CommandCLI()
    assert cmd.execute_shell_command('echo .')
    assert not cmd.check_docker_image_exists('apikit_cli:dev?')
    assert cmd.latest_version()
    assert cmd.get_cache_file()
    cmd.cache_running_containers('apikit_cli:dev?')
    assert cmd.get_running_containers()
    # assert cmd.clean_running_containers()
    cmd.execute()

    class TestComposite(CommandCLIComposite):
        commands = ['version', 'version']
    cmd = TestComposite()
    cmd.execute()


def test_check_command():
    from apikit_cli.apikit import CheckCommandCLI

    cmd = CheckCommandCLI()
    cmd.execute()


def test_format_command():
    from apikit_cli.apikit import FormatCommandCLI

    cmd = FormatCommandCLI()
    cmd.execute()


def test_lint_command():
    from apikit_cli.apikit import LintCommandCLI

    cmd = LintCommandCLI()
    cmd.execute()


def test_ping_command():
    from apikit_cli.apikit import PingCommandCLI

    cmd = PingCommandCLI()
    cmd.execute()
