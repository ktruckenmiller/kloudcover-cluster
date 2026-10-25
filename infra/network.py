from typing import List

import aws_cdk as cdk
from aws_cdk import Stack, aws_ec2 as ec2
from constructs import Construct

VPC_ID = "vpc-849531e0"
PUBLIC_ROUTE_TABLE_ID = "rtb-7737b513"
PUBLIC_SUBNETS = {
    "us-west-2a": "subnet-bc3193d8",
    "us-west-2b": "subnet-ed43849b",
    "us-west-2c": "subnet-9b2938c2",
}

# /64 indexes carved out of the VPC's /56: 0-2 existing public subnets, 3-5 IPv6-only compute subnets.
PUBLIC_SUBNET_IPV6_INDEX = 0
COMPUTE_SUBNET_IPV6_INDEX = 3
IPV6_SUBNET_COUNT = 8


class KloudCoverIpv6Network(Stack):
    """Adds IPv6 to the existing KloudCover VPC and creates IPv6-only subnets for ECS hosts.

    CloudFormation can't return the /56 that AWS assigns to an imported VPC, so this deploys in two passes:
    1. Deploy with `kloudcover:vpcIpv6CidrBlock` unset to associate an Amazon-provided /56.
    2. Set `kloudcover:vpcIpv6CidrBlock` in cdk.json to that /56 and deploy again to create the subnets.
    Set `kloudcover:associateVpcIpv6` to false if the VPC already had an IPv6 block before this stack.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.compute_subnets: List[ec2.ISubnet] = []

        if self.node.try_get_context("kloudcover:associateVpcIpv6") is not False:
            ec2.CfnVPCCidrBlock(
                self, "VpcIpv6Cidr", vpc_id=VPC_ID, amazon_provided_ipv6_cidr_block=True
            )

        vpc_ipv6_cidr = self.node.try_get_context("kloudcover:vpcIpv6CidrBlock")
        if not vpc_ipv6_cidr:
            return
        ipv6_blocks = cdk.Fn.cidr(vpc_ipv6_cidr, IPV6_SUBNET_COUNT, "64")

        # Dual-stack public subnets are needed for a dual-stack ALB and dual-stack EFS mount targets.
        for index, (az, subnet_id) in enumerate(PUBLIC_SUBNETS.items()):
            ec2.CfnSubnetCidrBlock(
                self,
                f"PublicIpv6Cidr{az[-1].upper()}",
                subnet_id=subnet_id,
                ipv6_cidr_block=cdk.Fn.select(PUBLIC_SUBNET_IPV6_INDEX + index, ipv6_blocks),
            )
        internet_gateway_id = self.node.try_get_context("kloudcover:internetGatewayId")
        if internet_gateway_id:
            ec2.CfnRoute(
                self,
                "PublicIpv6DefaultRoute",
                route_table_id=PUBLIC_ROUTE_TABLE_ID,
                destination_ipv6_cidr_block="::/0",
                gateway_id=internet_gateway_id,
            )

        egress_only_gateway = ec2.CfnEgressOnlyInternetGateway(self, "EgressOnlyIgw", vpc_id=VPC_ID)
        compute_route_table = ec2.CfnRouteTable(
            self,
            "ComputeRouteTable",
            vpc_id=VPC_ID,
            tags=[cdk.CfnTag(key="Name", value="kloudcover-ipv6-compute")],
        )
        ec2.CfnRoute(
            self,
            "ComputeIpv6DefaultRoute",
            route_table_id=compute_route_table.ref,
            destination_ipv6_cidr_block="::/0",
            egress_only_internet_gateway_id=egress_only_gateway.ref,
        )

        for index, az in enumerate(PUBLIC_SUBNETS):
            suffix = az[-1].upper()
            subnet = ec2.CfnSubnet(
                self,
                f"ComputeSubnet{suffix}",
                vpc_id=VPC_ID,
                availability_zone=az,
                ipv6_native=True,
                ipv6_cidr_block=cdk.Fn.select(COMPUTE_SUBNET_IPV6_INDEX + index, ipv6_blocks),
                assign_ipv6_address_on_creation=True,
                enable_dns64=False,
                private_dns_name_options_on_launch={
                    "HostnameType": "resource-name",
                    "EnableResourceNameDnsAAAARecord": True,
                    "EnableResourceNameDnsARecord": False,
                },
                tags=[cdk.CfnTag(key="Name", value=f"kloudcover-ipv6-compute-{az[-1]}")],
            )
            ec2.CfnSubnetRouteTableAssociation(
                self,
                f"ComputeSubnet{suffix}Routes",
                subnet_id=subnet.ref,
                route_table_id=compute_route_table.ref,
            )
            self.compute_subnets.append(
                ec2.Subnet.from_subnet_attributes(
                    self,
                    f"ComputeSubnet{suffix}Ref",
                    subnet_id=subnet.ref,
                    availability_zone=az,
                    route_table_id=compute_route_table.ref,
                )
            )
