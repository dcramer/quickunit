nose-quickunit
==============

Given standard test setup, will determine which tests need to run against a given diff.

For example, say you're working in your branch called my-new-sexy-feature, which modifies the following files::

src/foo/bar/__init__.py
src/foo/bar/baz.py
src/foo/biz.py

Now if we run with the default options, ``nosetests --with-quickunit``, it will look for tests (by default) in
the following base directories::

tests/foo/bar/*
tests/foo/biz/*

It will also report coverage based on the tests run, and optionally dump that to a JSON file.

Config
------

If you want to support multiple directories for searching (let's say you break up unittests from integration tests)
you can do that as well:

--quickunit-prefix=tests/unit/ --quickunit-prefix=tests/integration/

Or, if you'd prefer, via ``setup.cfg``::

quickunit-prefix = tests/unit
                   tests/integration

To output the coverage report as a JSON file, you can use simply use the ``quickunit-output`` option::

--quickunit-output=coverage.json

Or, via ``setup.cfg``::

quickunit-json = -