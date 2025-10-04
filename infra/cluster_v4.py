import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_efs as efs,
    aws_autoscaling as autoscaling,
)
from constructs import Construct


class ECSClusterV4(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, environment: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.environ = environment
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "vpc",
            vpc_id="vpc-0cb5fe5c0a27a66da",
            # availability_zones=["us-west-2a", "us-west-2b", "us-west-2c"],
        )
        # self.alb_sg = ec2.SecurityGroup.from_security_group_id(
        #     self, "ALBSG", security_group_id="sg-d8ab3ca5", mutable=True
        # )
        # self.db_sg = ec2.SecurityGroup.from_security_group_id(
        #     self, "DBSG", security_group_id="sg-059aa6ca5b014187b"
        # )
        self.default_role = iam.Role.from_role_arn(
            self,
            "ImportedRole",
            role_arn=cdk.Fn.sub(
                "arn:aws:iam::${AWS::AccountId}:instance-profile/ecsInstanceRole"
            ),
        )
        self.file_system = efs.FileSystem.from_file_system_attributes(
            self,
            "Files",
            file_system_id="fs-df827476",
            security_group=ec2.SecurityGroup.from_lookup_by_id(
                self, "SGfilez", security_group_id="sg-0def9e6b"
            ),
        )
        # self.cluster = self.get_cluster()

    def get_cluster(self):
        cluster = ecs.Cluster(
            self,
            "KloudCoverCluster",
            container_insights=False,
            cluster_name=f"{self.environ}-kloudcover-v4",
            vpc=self.vpc,
        )

        sg = ec2.SecurityGroup(self, "SG", allow_all_outbound=True, vpc=self.vpc)
        sg.add_ingress_rule(
            peer=self.alb_sg,
            connection=ec2.Port.all_traffic(),
            description="Allow inbound HTTPS",
        )
        cap_providers = []
        for asg_name in ["small"]:
            asg_obj, cap_obj = self.get_asg(asg_name, sg, "0.010", asg_name.upper())
            cluster.add_asg_capacity_provider(provider=cap_obj)

        return cluster
