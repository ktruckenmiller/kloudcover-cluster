# kloudcover-cluster
ECS Clusters for KloudCover

## IPv6 clusters (`{env}-kloudcover-v4`)

The v4 clusters run their container instances in IPv6-only subnets of `vpc-849531e0`, so the hosts have no public IPv4. They reach AWS through dual-stack endpoints, and their outbound traffic leaves through an egress-only internet gateway.

1. `cdk deploy kloudcover-ipv6-network` associates an Amazon-provided IPv6 /56 with the VPC.
2. Read the /56 and the internet gateway ID:
   `aws ec2 describe-vpcs --vpc-ids vpc-849531e0 --query 'Vpcs[0].Ipv6CidrBlockAssociationSet[].Ipv6CidrBlock'`
   `aws ec2 describe-internet-gateways --filters Name=attachment.vpc-id,Values=vpc-849531e0 --query 'InternetGateways[].InternetGatewayId'`
3. Set `kloudcover:vpcIpv6CidrBlock` and `kloudcover:internetGatewayId` in `cdk.json`. Then run `cdk deploy kloudcover-ipv6-network` again. This adds IPv6 to the public subnets, adds a `::/0` route to the internet gateway, and creates the IPv6-only compute subnets.
4. `cdk deploy staging-cluster-v2` (the v4 cluster stacks only synthesize once step 3 is configured).

If the VPC already had an IPv6 block before step 1, set `kloudcover:associateVpcIpv6` to `false` and start at step 2.

Before tasks can run on v4, do these outside this repo:
- Recreate the EFS `fs-df827476` mount targets as `DUAL_STACK`, one AZ at a time.
- Make the ALB `dualstack`, and allow `::/0` on its security group.
- Register services through IPv6 target groups.
- Reference ECR images through `601394826940.dkr-ecr.us-west-2.on.aws/...`.
- Switch RDS to `--network-type DUAL` (it must not be publicly accessible).
