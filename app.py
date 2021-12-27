#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra.cluster import ECSCluster


app = cdk.App()
ECSCluster(
    app,
    "cluster-stack",
    environment="stage",
    env=cdk.Environment(account="601394826940", region="us-west-2"),
)

app.synth()
