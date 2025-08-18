def test_success():
    assert 1 == 1


def test_fail():
    print('logmsg')
    assert 1 == 2


def test_error():
    print('logmsg')
    raise Exception('ops')
