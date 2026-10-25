import json
from typing import List

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_efs as efs,
    aws_autoscaling as autoscaling,
)
from constructs import Construct

from infra.network import VPC_ID

DOCKER_DAEMON_CONFIG = {
    "ipv6": True,
    "fixed-cidr-v6": "fd00:d0c::/64",
    "ip6tables": True,
    "experimental": True,
}


class ECSClusterV4(Stack):
    """ECS cluster whose container instances live in IPv6-only subnets with no public IPv4."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        compute_subnets: List[ec2.ISubnet],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.environ = environment
        self.compute_subnets = compute_subnets
        self.vpc = ec2.Vpc.from_lookup(self, "vpc", vpc_id=VPC_ID)
        self.alb_sg = ec2.SecurityGroup.from_security_group_id(
            self, "ALBSG", security_group_id="sg-d8ab3ca5", mutable=True
        )
        self.db_sg = ec2.SecurityGroup.from_security_group_id(
            self, "DBSG", security_group_id="sg-059aa6ca5b014187b"
        )
        self.default_role = iam.Role.from_role_arn(
            self,
            "ImportedRole4",
            role_arn=cdk.Fn.sub(
                "arn:aws:iam::${AWS::AccountId}:instance-profile/ecsInstanceRole"
            ),
        )
        self.file_system = efs.FileSystem.from_file_system_attributes(
            self,
            "Files4",
            file_system_id="fs-df827476",
            security_group=ec2.SecurityGroup.from_lookup_by_id(
                self, "SGfilez", security_group_id="sg-0def9e6b"
            ),
        )
        self.cluster = self.get_cluster()

    def get_user_data(self) -> ec2.UserData:
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "echo ECS_INSTANCE_IP_COMPATIBILITY=ipv6 >> /etc/ecs/ecs.config",
            # Bridge-mode tasks only get IPv6 egress once Docker's bridge has IPv6 enabled.
            f"echo '{json.dumps(DOCKER_DAEMON_CONFIG)}' > /etc/docker/daemon.json",
            "systemctl restart docker",
            # CDK only blocks the IPv4 IMDS endpoint from containers; block the IPv6 one too.
            "ip6tables --insert FORWARD 1 --in-interface docker+ --destination fd00:ec2::254/128 --jump DROP",
            "echo AWS_USE_DUALSTACK_ENDPOINT=true >> /etc/environment",
            "dnf upgrade -y",
            "dnf install -y amazon-efs-utils jq",
            "if [ -f /etc/amazon/ssm/amazon-ssm-agent.json.template ]; then"
            " cfg=/etc/amazon/ssm/amazon-ssm-agent.json;"
            ' [ -f "$cfg" ] || cp "$cfg.template" "$cfg";'
            " jq '.Agent.Region = \"us-west-2\" | .Agent.UseDualStackEndpoint = true' \"$cfg\" > \"$cfg.tmp\""
            ' && mv "$cfg.tmp" "$cfg";'
            " systemctl try-restart amazon-ssm-agent;"
            " fi",
            # Requires dual-stack EFS mount targets in the VPC.
            f"mkdir -p /efs && echo '{self.file_system.file_system_id}:/ /efs efs defaults,_netdev' >> /etc/fstab && mount -a -t efs defaults",
        )
        return user_data

    def get_launch_template(self, asg_name: str, asg_sg: ec2.SecurityGroup) -> ec2.LaunchTemplate:
        launch_template = ec2.LaunchTemplate(
            self,
            f"{asg_name}LaunchTemplate",
            machine_image=ecs.EcsOptimizedImage.amazon_linux2023(ecs.AmiHardwareType.ARM),
            role=self.default_role,
            user_data=self.get_user_data(),
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(
                        delete_on_termination=True,
                        encrypted=False,
                        volume_size=30,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                    ),
                )
            ],
            http_protocol_ipv6=True,
        )
        # Network interfaces aren't exposed by the L2; ECS needs a primary IPv6 so bridge/host
        # tasks can register with IPv6 target groups. Security groups must move onto the interface.
        cfn_launch_template: ec2.CfnLaunchTemplate = launch_template.node.default_child
        cfn_launch_template.add_property_override(
            "LaunchTemplateData.NetworkInterfaces",
            [
                {
                    "DeviceIndex": 0,
                    "Ipv6AddressCount": 1,
                    "PrimaryIpv6": True,
                    "Groups": [asg_sg.security_group_id, self.db_sg.security_group_id],
                }
            ],
        )
        return launch_template

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
            vpc_subnets=ec2.SubnetSelection(subnets=self.compute_subnets),
            mixed_instances_policy=autoscaling.MixedInstancesPolicy(
                launch_template=self.get_launch_template(asg_name, asg_sg),
                instances_distribution=autoscaling.InstancesDistribution(
                    on_demand_percentage_above_base_capacity=0,
                    spot_allocation_strategy=autoscaling.SpotAllocationStrategy.PRICE_CAPACITY_OPTIMIZED,
                    spot_max_price=spot_price,
                ),
                launch_template_overrides=[
                    autoscaling.LaunchTemplateOverrides(
                        instance_type=ec2.InstanceType.of(
                            ec2.InstanceClass.BURSTABLE4_GRAVITON,
                            getattr(ec2.InstanceSize, instance_size),
                        )
                    )
                ],
            ),
            min_capacity=0,
            max_capacity=6,
            capacity_rebalance=True,
            new_instances_protected_from_scale_in=False,
            update_policy=autoscaling.UpdatePolicy.rolling_update(max_batch_size=1),
        )
        self.file_system.connections.allow_default_port_from(asg_sg)

        capacity_provider = ecs.AsgCapacityProvider(
            self,
            f"{asg_name}AsgCapacityProvider",
            auto_scaling_group=auto_scaling_group,
            enable_managed_scaling=True,
            spot_instance_draining=True,
        )
        return auto_scaling_group, capacity_provider

    def get_cluster(self):
        cluster = ecs.Cluster(
            self,
            "KloudCoverClusterV4",
            cluster_name=f"{self.environ}-kloudcover-v4",
            vpc=self.vpc,
        )

        sg = ec2.SecurityGroup(
            self,
            "SG",
            vpc=self.vpc,
            allow_all_outbound=True,
            allow_all_ipv6_outbound=True,
        )
        sg.add_ingress_rule(
            peer=self.alb_sg,
            connection=ec2.Port.all_traffic(),
            description="Allow inbound from the ALB",
        )
        for asg_name in ["small"]:
            _, cap_obj = self.get_asg(asg_name, sg, "0.018", asg_name.upper())
            cluster.add_asg_capacity_provider(provider=cap_obj)

        return cluster
