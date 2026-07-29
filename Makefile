.PHONY: test demo

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
	PYTHONPATH=src python3 -m compileall -q src examples

demo:
	PYTHONPATH=src python3 -m cdmx_bayesopt --iterations 20 --gif --output runs/demo
