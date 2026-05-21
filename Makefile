.PHONY: test install

install:
	pip install -r requirements.txt
	pip install -e .

test:
	pytest
