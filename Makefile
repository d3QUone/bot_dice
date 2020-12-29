#!/bin/sh
VERBOSE=1

test:
	poetry run nosetests --verbosity $(VERBOSE)

release:
	git log -1 --pretty='%H' > .release
