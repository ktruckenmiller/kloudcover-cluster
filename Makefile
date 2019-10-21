REGION ?= us-west-2

put-pipeline:
	docker run -it --rm \
		-v ${PWD}:${PWD} \
		-w ${PWD} \
		-e AWS_DEFAULT_REGION=$(REGION) \
		-e IAM_ROLE=arn:aws:iam::601394826940:role/cloudformation \
		ktruckenmiller/ecs-cluster-deployer:9df1f04ab43113ed3fa5aeee26ff8bcfb02af3aa put-pipeline
.PHONY: put-pipeline
