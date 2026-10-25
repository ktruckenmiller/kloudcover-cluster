from aws_cdk import CfnResource, Stack
from aws_cdk import aws_iam as iam
from constructs import Construct

ACCOUNT_ID = "601394826940"
REGION = "us-west-2"


class SharedDeployIam(Stack):
    """Shared IAM for WordPress CloudFormation deploys (ECS instance + CFN service role)."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        CfnResource(
            self,
            "DroneWordpressDeploy",
            type="AWS::IAM::RolePolicy",
            properties={
                "RoleName": "ecsInstanceRole",
                "PolicyName": "drone-wordpress-deploy",
                "PolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "CloudFormationWordPressStacksUsWest2",
                        "Effect": "Allow",
                        "Action": [
                            "cloudformation:CreateStack",
                            "cloudformation:UpdateStack",
                            "cloudformation:DeleteStack",
                            "cloudformation:DescribeStacks",
                            "cloudformation:DescribeStackEvents",
                            "cloudformation:DescribeStackResources",
                            "cloudformation:GetTemplate",
                            "cloudformation:GetTemplateSummary",
                            "cloudformation:ValidateTemplate",
                            "cloudformation:CreateChangeSet",
                            "cloudformation:DescribeChangeSet",
                            "cloudformation:ExecuteChangeSet",
                            "cloudformation:DeleteChangeSet",
                            "cloudformation:ListChangeSets",
                            "cloudformation:ListStackResources",
                        ],
                        "Resource": [
                            f"arn:aws:cloudformation:{REGION}:{ACCOUNT_ID}:stack/quietdrivemusic-*/*",
                            f"arn:aws:cloudformation:{REGION}:{ACCOUNT_ID}:stack/atlastractor-*/*",
                            f"arn:aws:cloudformation:{REGION}:{ACCOUNT_ID}:stack/motioncare-*/*",
                        ],
                    },
                    {
                        "Sid": "PassCfnServiceRole",
                        "Effect": "Allow",
                        "Action": "iam:PassRole",
                        "Resource": f"arn:aws:iam::{ACCOUNT_ID}:role/cfn-deploy",
                        "Condition": {
                            "StringEquals": {
                                "iam:PassedToService": "cloudformation.amazonaws.com"
                            }
                        },
                    },
                    {
                        "Sid": "ElbPriorityDiscovery",
                        "Effect": "Allow",
                        "Action": [
                            "elasticloadbalancing:DescribeLoadBalancers",
                            "elasticloadbalancing:DescribeListeners",
                            "elasticloadbalancing:DescribeRules",
                        ],
                        "Resource": "*",
                        "Condition": {
                            "StringEquals": {"aws:RequestedRegion": REGION}
                        },
                    },
                ],
                },
            },
        )

        iam.CfnRole(
            self,
            "CfnDeployRole",
            role_name="cfn-deploy",
            assume_role_policy_document={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "cloudformation.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            },
        )

        CfnResource(
            self,
            "CfnDeployWordpressStacks",
            type="AWS::IAM::RolePolicy",
            properties={
                "RoleName": "cfn-deploy",
                "PolicyName": "wordpress-stacks",
                "PolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PassRolesUsedByWordPressStacks",
                        "Effect": "Allow",
                        "Action": "iam:PassRole",
                        "Resource": [
                            f"arn:aws:iam::{ACCOUNT_ID}:role/ecsEventsRole",
                            f"arn:aws:iam::{ACCOUNT_ID}:role/kloudcover-alb-ServiceRole",
                            f"arn:aws:iam::{ACCOUNT_ID}:role/quietdrivemusic-*",
                            f"arn:aws:iam::{ACCOUNT_ID}:role/atlastractor-*",
                            f"arn:aws:iam::{ACCOUNT_ID}:role/motioncare-*",
                        ],
                        "Condition": {
                            "StringEquals": {
                                "iam:PassedToService": [
                                    "ecs.amazonaws.com",
                                    "events.amazonaws.com",
                                    "lambda.amazonaws.com",
                                ]
                            }
                        },
                    },
                    {
                        "Sid": "IamRolesAndPoliciesForStacks",
                        "Effect": "Allow",
                        "Action": [
                            "iam:CreateRole",
                            "iam:DeleteRole",
                            "iam:GetRole",
                            "iam:UpdateRole",
                            "iam:PutRolePolicy",
                            "iam:DeleteRolePolicy",
                            "iam:GetRolePolicy",
                            "iam:ListAttachedRolePolicies",
                            "iam:ListRolePolicies",
                            "iam:TagRole",
                            "iam:UntagRole",
                        ],
                        "Resource": [
                            f"arn:aws:iam::{ACCOUNT_ID}:role/quietdrivemusic-*",
                            f"arn:aws:iam::{ACCOUNT_ID}:role/atlastractor-*",
                            f"arn:aws:iam::{ACCOUNT_ID}:role/motioncare-*",
                        ],
                    },
                    {
                        "Sid": "ElbTargetGroupsAndRulesUsWest2",
                        "Effect": "Allow",
                        "Action": [
                            "elasticloadbalancing:CreateTargetGroup",
                            "elasticloadbalancing:DeleteTargetGroup",
                            "elasticloadbalancing:ModifyTargetGroup",
                            "elasticloadbalancing:ModifyTargetGroupAttributes",
                            "elasticloadbalancing:DescribeTargetGroups",
                            "elasticloadbalancing:DescribeTargetGroupAttributes",
                            "elasticloadbalancing:CreateRule",
                            "elasticloadbalancing:DeleteRule",
                            "elasticloadbalancing:ModifyRule",
                            "elasticloadbalancing:DescribeRules",
                            "elasticloadbalancing:AddListenerCertificates",
                            "elasticloadbalancing:RemoveListenerCertificates",
                            "elasticloadbalancing:DescribeListenerCertificates",
                        ],
                        "Resource": "*",
                        "Condition": {
                            "StringEquals": {"aws:RequestedRegion": REGION}
                        },
                    },
                    {
                        "Sid": "EcsUsWest2",
                        "Effect": "Allow",
                        "Action": [
                            "ecs:CreateService",
                            "ecs:UpdateService",
                            "ecs:DeleteService",
                            "ecs:DescribeServices",
                            "ecs:RegisterTaskDefinition",
                            "ecs:DeregisterTaskDefinition",
                            "ecs:DescribeTaskDefinition",
                            "ecs:TagResource",
                            "ecs:UntagResource",
                        ],
                        "Resource": "*",
                        "Condition": {
                            "StringEquals": {"aws:RequestedRegion": REGION}
                        },
                    },
                    {
                        "Sid": "LogsUsWest2",
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:DeleteLogGroup",
                            "logs:DescribeLogGroups",
                            "logs:PutRetentionPolicy",
                            "logs:TagLogGroup",
                            "logs:UntagLogGroup",
                            "logs:ListTagsLogGroup",
                        ],
                        "Resource": [
                            f"arn:aws:logs:{REGION}:{ACCOUNT_ID}:log-group:quietdrivemusic-*",
                            f"arn:aws:logs:{REGION}:{ACCOUNT_ID}:log-group:atlastractor-*",
                            f"arn:aws:logs:{REGION}:{ACCOUNT_ID}:log-group:motioncare-*",
                        ],
                    },
                    {
                        "Sid": "LambdaHealthCheckUsWest2",
                        "Effect": "Allow",
                        "Action": [
                            "lambda:CreateFunction",
                            "lambda:DeleteFunction",
                            "lambda:UpdateFunctionCode",
                            "lambda:UpdateFunctionConfiguration",
                            "lambda:GetFunction",
                            "lambda:GetFunctionConfiguration",
                            "lambda:AddPermission",
                            "lambda:RemovePermission",
                            "lambda:TagResource",
                            "lambda:UntagResource",
                            "lambda:PublishVersion",
                        ],
                        "Resource": [
                            f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:quietdrivemusicHealthCheck-*",
                            f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:atlastractorHealthCheck-*",
                            f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:motioncareHealthCheck-*",
                        ],
                    },
                    {
                        "Sid": "EventsRulesUsWest2",
                        "Effect": "Allow",
                        "Action": [
                            "events:PutRule",
                            "events:DeleteRule",
                            "events:DescribeRule",
                            "events:EnableRule",
                            "events:DisableRule",
                            "events:PutTargets",
                            "events:RemoveTargets",
                            "events:ListTargetsByRule",
                            "events:TagResource",
                            "events:UntagResource",
                        ],
                        "Resource": [
                            f"arn:aws:events:{REGION}:{ACCOUNT_ID}:rule/quietdrivemusic-*",
                            f"arn:aws:events:{REGION}:{ACCOUNT_ID}:rule/atlastractor-*",
                            f"arn:aws:events:{REGION}:{ACCOUNT_ID}:rule/motioncare-*",
                        ],
                    },
                    {
                        "Sid": "CloudWatchAlarmsUsWest2",
                        "Effect": "Allow",
                        "Action": [
                            "cloudwatch:PutMetricAlarm",
                            "cloudwatch:DeleteAlarms",
                            "cloudwatch:DescribeAlarms",
                            "cloudwatch:TagResource",
                            "cloudwatch:UntagResource",
                        ],
                        "Resource": [
                            f"arn:aws:cloudwatch:{REGION}:{ACCOUNT_ID}:alarm:quietdrivemusic-*",
                            f"arn:aws:cloudwatch:{REGION}:{ACCOUNT_ID}:alarm:atlastractor-*",
                            f"arn:aws:cloudwatch:{REGION}:{ACCOUNT_ID}:alarm:motioncare-*",
                        ],
                    },
                    {
                        "Sid": "SnsAlarmActions",
                        "Effect": "Allow",
                        "Action": [
                            "sns:GetTopicAttributes",
                            "sns:ListTopics",
                        ],
                        "Resource": f"arn:aws:sns:{REGION}:{ACCOUNT_ID}:kevins-cell",
                    },
                    {
                        "Sid": "CloudFormationReadForExports",
                        "Effect": "Allow",
                        "Action": [
                            "cloudformation:ListExports",
                            "cloudformation:DescribeStacks",
                        ],
                        "Resource": "*",
                    },
                ],
                },
            },
        )
