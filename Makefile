.PHONY: test simulate-bayesopt color-lab

PYTHON ?= python3

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v
	PYTHONPATH=src $(PYTHON) -m compileall -q src

simulate-bayesopt:
	CDMX_SIMULATE=1 PYTHONPATH=src $(PYTHON) -m utils.cli '#4A80C0' --iterations 10 --initial 4 --candidates 300 --output runs/simulated-campaign

color-lab:
	PYTHONPATH=src $(PYTHON) -m web.app --simulate
