NAME := sneakpeek
PY_INSTALL_STAMP := .py.install.stamp
JS_INSTALL_STAMP := .js.install.stamp
POETRY := $(shell command -v poetry 2> /dev/null)
YARN := $(shell command -v yarn 2> /dev/null)
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

.DEFAULT_GOAL := help


.PHONY: help
help: ##Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | sed -e 's/\(\:.*\#\#\)/\:\ /' | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

install-py: $(PY_INSTALL_STAMP) ##Install python dependencies (Poetry is required)
$(PY_INSTALL_STAMP): pyproject.toml poetry.lock
	@if [ -z $(POETRY) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	$(POETRY) --version
	$(POETRY) install --all-extras --with remotesettings,taskcluster --no-ansi --no-interaction --verbose
	touch $(PY_INSTALL_STAMP)

install-js: $(JS_INSTALL_STAMP) ##Install JS dependencies (Yarn is required)
$(JS_INSTALL_STAMP): front/package.json front/yarn.lock
	@if [ -z $(YARN) ]; then echo "YARN could not be found. See https://yarnpkg.com/"; exit 2; fi
	$(YARN) --version
	cd $(ROOT_DIR)/front; $(YARN) install
	touch $(JS_INSTALL_STAMP)

install: install-py install-js ##Install all dependencies

.PHONY: test
test: $(PY_INSTALL_STAMP) ##Run tests
	$(POETRY) run pytest

build-ui: ##Build frontend
	$(YARN) --cwd $(ROOT_DIR)/front/ quasar build

build-docs: $(PY_INSTALL_STAMP) ##Build documentation
	rm -rf $(ROOT_DIR)/docs/_build
	$(POETRY) run sphinx-build $(ROOT_DIR)/docs $(ROOT_DIR)/docs/_build
	rm -rf $(ROOT_DIR)/sneakpeek/static/docs/
	mkdir -p $(ROOT_DIR)/sneakpeek/static/docs/
	cp -r $(ROOT_DIR)/docs/_build/** $(ROOT_DIR)/sneakpeek/static/docs/

build-py: ##Build Python package
	$(POETRY) build

build: build-ui build-docs build-py ##Build everything

.PHONY: clean
clean: ##Cleanup
	find . -type d -name "__pycache__" | xargs rm -rf {};
	find . -type d -name ".pytest_cache" | xargs rm -rf {};
	rm -rf $(PY_INSTALL_STAMP) $(JS_INSTALL_STAMP) .coverage .mypy_cache