#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra.cluster import ECSCluster
from infra.cluster_v4 import ECSClusterV4
from infra.network import KloudCoverIpv6Network

env = cdk.Environment(account="601394826940", region="us-west-2")

app = cdk.App()
network = KloudCoverIpv6Network(app, "kloudcover-ipv6-network", env=env)
for environment in ["staging", "production"]:
    ECSCluster(
        app,
        f"{environment}-cluster",
        environment=environment,
        env=env,
    )
    if network.compute_subnets:
        ECSClusterV4(
            app,
            f"{environment}-cluster-v2",
            environment=environment,
            compute_subnets=network.compute_subnets,
            env=env,
        )

app.synth()
