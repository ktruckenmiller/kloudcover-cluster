import aws_cdk as cdk
from aws_cdk import (
    Duration,
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
        self.alb_sg = ec2.SecurityGroup.from_security_group_id(
            self, "ALBSG", security_group_id="sg-d8ab3ca5", mutable=True
        )
        self.db_sg = ec2.SecurityGroup.from_security_group_id(
            self, "DBSG", security_group_id="sg-059aa6ca5b014187b"
        )
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
        self.cluster = self.get_cluster()

    def get_asg(
        self,
        asg_name: str,
        asg_sg: ec2.SecurityGroup,
        spot_price: str,
        instance_size: str,
    ):
        auto_scaling_group = autoscaling.AutoScalingGroup(
            self,
            f"{asg_name}ASG",
            vpc=self.vpc,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON,
                getattr(ec2.InstanceSize, instance_size),
            ),
            block_devices=[
                autoscaling.BlockDevice(
                    device_name="/dev/xvda",
                    volume=autoscaling.BlockDeviceVolume.ebs(
                        delete_on_termination=True,
                        encrypted=False,
                        volume_size=30,
                        volume_type=autoscaling.EbsDeviceVolumeType.GP3,
                    ),
                )
            ],
            instance_monitoring=autoscaling.Monitoring.BASIC,
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(ecs.AmiHardwareType.ARM),
            min_capacity=2,
            max_capacity=6,
            role=self.default_role,
            spot_price="0.015",
            new_instances_protected_from_scale_in=False,
            update_policy=autoscaling.UpdatePolicy.rolling_update(
                max_batch_size=2,
                min_instances_in_service=2,
            ),
            signals=autoscaling.Signals.wait_for_all(timeout=Duration.minutes(5)),
        )
        auto_scaling_group.add_security_group(asg_sg)
        auto_scaling_group.add_security_group(self.db_sg)
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
            f"{asg_name}AsgCapacityProvider",
            auto_scaling_group=auto_scaling_group,
            enable_managed_scaling=True,
            # enable_managed_termination_protection=True,
            can_containers_access_instance_role=False,
            spot_instance_draining=True,
        )
        return auto_scaling_group, capacity_provider

    def get_cluster(self):
        cluster = ecs.Cluster(
            self,
            "KloudCoverCluster",
            container_insights=False,
            cluster_name=f"{self.environ}-kloudcover-v3",
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
