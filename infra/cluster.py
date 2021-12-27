import aws_cdk as cdk
from aws_cdk import (
    # Duration,
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_efs as efs,
    aws_autoscaling as autoscaling,
    # aws_sqs as sqs,
)
from constructs import Construct


class ECSCluster(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, environment: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.environ = environment
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "vpc",
            vpc_id="vpc-849531e0",
            # availability_zones=["us-west-2a", "us-west-2b", "us-west-2c"],
        )
        self.file_system = efs.FileSystem.from_file_system_attributes(
            self,
            "Files",
            file_system_id="fs-df827476",
            security_group=ec2.SecurityGroup.from_lookup_by_id(
                self, "SGfilez", security_group_id="sg-0def9e6b"
            ),
        )
        self.cluster = self.get_cluster()

    def get_cluster(self):
        cluster = ecs.Cluster(
            self,
            "KloudCoverCluster",
            container_insights=True,
            cluster_name=f"{self.environ}-kloudcover-v1",
            vpc=self.vpc,
        )
        role = iam.Role.from_role_arn(
            self,
            "ImportedRole",
            role_arn=cdk.Fn.sub(
                "arn:aws:iam::${AWS::AccountId}:instance-profile/ecsInstanceRole"
            ),
        )
        auto_scaling_group = autoscaling.AutoScalingGroup(
            self,
            "ASG",
            vpc=self.vpc,
            instance_type=ec2.InstanceType("t3a.small"),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
            min_capacity=0,
            max_capacity=6,
            role=role,
            spot_price="0.01",
        )
        self.file_system.connections.allow_default_port_from(auto_scaling_group)
        auto_scaling_group.user_data.add_commands(
            "yum check-update -y",
            "yum upgrade -y",
            "yum install -y amazon-efs-utils",
            "yum install -y nfs-utils",
            "mkdir -p /efs",
            f'test -f "/sbin/mount.efs" && echo "{self.file_system.file_system_id}:/ /efs efs defaults,_netdev" >> /etc/fstab || echo "{self.file_system.file_system_id}.efs.{self.region}.amazonaws.com:/ /efs nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev 0 0" >> /etc/fstab',
            "mount -a -t efs,nfs4 defaults",
        )

        capacity_provider = ecs.AsgCapacityProvider(
            self,
            "AsgCapacityProvider",
            auto_scaling_group=auto_scaling_group,
            enable_managed_scaling=True,
            enable_managed_termination_protection=True,
            can_containers_access_instance_role=True,
            spot_instance_draining=True,
        )
        cluster.add_asg_capacity_provider(capacity_provider)
        return cluster
