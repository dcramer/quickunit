develop:
	pip install -e . --use-mirrors
	pip install -q "file://`pwd`#egg=quickunit[tests]" --use-mirrors

test: develop
	nosetests

qtest: develop
	nosetests --with-quickunit
