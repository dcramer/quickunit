nose-quickunit
==============

Given standard test setup, will determine which tests need to run against a given diff.

For example, say you're working in your branch called my-new-sexy-feature, which modifies the following files::

    src/foo/bar/__init__.py
    src/foo/bar/baz.py
    src/foo/biz.py

Now if we run with the default options, ``nosetests --with-quickunit``, it will look for tests (by default) in
the following base directories::

    tests/src/foo/bar/*
    tests/src/foo/biz/*

(It does this by analyzing the diff against `git merge-base HEAD master`, and determining which files you've changed
are tests, including them, and which files containing test coverage in a parallel directory.)

.. note:: As of 0.5.0 nose-quickunit no longer reports test coverage

Config
------

If you want to support multiple directories for searching (let's say you break up unittests from integration tests)
you can do that as well::

    --quickunit-prefix=tests/unit/ --quickunit-prefix=tests/integration/

Or, if you'd prefer, via ``setup.cfg``::

    quickunit-prefix = tests/unit
                       tests/integration

Or, via ``setup.cfg``::

    quickunit-json = -
