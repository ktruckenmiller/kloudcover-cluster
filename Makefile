REGION ?= us-west-2

DKR_CMD:=docker run -it --rm\
	-v ${PWD}:/work \
	-w /work \
	-v ~/.aws:/root/.aws:ro \
	ktruckenmiller/aws-cdk cdk

list:
	${DKR_CMD} list

deploy:
	${DKR_CMD} deploy --all

.PHONY: put-pipeline
