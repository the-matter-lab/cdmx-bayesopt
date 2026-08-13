.PHONY: test simulate-bayesopt color-lab

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
	PYTHONPATH=src python3 -m compileall -q src

simulate-bayesopt:
	CDMX_SIMULATE=1 PYTHONPATH=src python3 -m cdmx_bayesopt '#4A80C0' --iterations 10 --initial 4 --candidates 300 --output runs/simulated-campaign

color-lab:
	PYTHONPATH=src python3 -m cdmx_bayesopt.webapp --simulate
