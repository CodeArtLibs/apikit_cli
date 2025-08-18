import os


def test_success():
    assert 1 == 1


def test_fail():
    print('logmsg')
    assert 1 == 2


def test_error():
    print('logmsg')
    raise Exception('ops')


def test_env():
    assert os.getenv('DEV_ENV')
    assert os.getenv('TEST_ENV')
    assert os.getenv('API_VERSION') == 'test'


def test_pytest_ini():
    assert os.getenv('SOME_ENV_VAR') == 'abc'
    assert os.getenv('ANOTHER_ENV_VAR') == 'def'
