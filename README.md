APIKit CLI
=================================================

# Development

```shell
make prepare
make deps
make format
make lint
make test
make build
make test_bin
make update
make copy
make all
```


# Manual testing

```shell
cd sample_app
make shell
make $ACTION
make test_env
make test_ci
make test_dev
make test_cd
make test_debug
make test
```


# Running

```shell
env/bin/python apikit_cli/apikit.py --help
apikit version
```


# Live

```shell
make publish
```


# Binary hash check

```shell
# https://github.com/CodeArtLibs/apikit_cli/releases
apikit version
shasum -a 256 apikit
```
