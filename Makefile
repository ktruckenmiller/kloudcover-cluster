
<<<<<<< HEAD
setup:
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt


=======
DKR_CMD:=docker run -it --rm\
	-v ${PWD}:/work \
	-w /work \
	-e ENVIRON \
	-v ~/.aws:/root/.aws:ro \
	ktruckenmiller/aws-cdk cdk

list:
	${DKR_CMD} list
diff:
	${DKR_CMD} diff
deploy:
	${DKR_CMD} deploy --all

.PHONY: put-pipeline
>>>>>>> ff671ce (Adding durations)
