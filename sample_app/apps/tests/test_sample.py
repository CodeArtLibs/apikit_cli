import geopy  # testing requirements-app.txt was installed


def test_sample():
    assert geopy.__version__
    assert 1 == 2
