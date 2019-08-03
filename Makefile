REGION ?= us-west-2

put-pipeline:
	docker run -it --rm \
		-v ${PWD}:${PWD} \
		-w ${PWD} \
		-e AWS_DEFAULT_REGION=$(REGION) \
		-e IAM_ROLE=arn:aws:iam::601394826940:role/cloudformation \
		ktruckenmiller/ecs-cluster-deployer put-pipeline
.PHONY: put-pipeline
