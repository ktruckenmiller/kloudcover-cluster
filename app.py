#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra.cluster import ECSCluster
from infra.cluster_v4 import ECSClusterV4

app = cdk.App()
for environment in ["staging", "production"]:
    ECSCluster(
        app,
        f"{environment}-cluster",
        environment=environment,
        env=cdk.Environment(account="601394826940", region="us-west-2"),
    )
    ECSClusterV2(
        app,
        f"{environment}-cluster-v2",
        environment=environment,
        env=cdk.Environment(account="601394826940", region="us-west-2"),
    )

app.synth()
