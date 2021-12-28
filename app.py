#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra.cluster import ECSCluster

environment = os.environ.get("ENVIRON", "staging")

app = cdk.App()
ECSCluster(
    app,
    f"{environment}-cluster",
    environment=environment,
    env=cdk.Environment(account="601394826940", region="us-west-2"),
)

app.synth()
