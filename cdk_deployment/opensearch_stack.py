from aws_cdk import (
    Stack,
    aws_opensearchservice as opensearch,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    Duration,
    Tags,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct
import os


class OpenSearchDomainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add tags to the stack (must comply with SCP policies)
        Tags.of(self).add("Environment", "testing")
        Tags.of(self).add("Owner", "tmd-cloud")
        Tags.of(self).add("IsCritical", "true")
        Tags.of(self).add("IsTemporal", "false")
        Tags.of(self).add("Project", "cloud-deployments")
        Tags.of(self).add("ProjectName", "cloud-deployments")
        Tags.of(self).add("Repository", "cloud-deployments")

        # Domain name derived from stack name (must be lowercase and hyphenated)
        domain_name = f"{self.stack_name}-domain".lower()

        # Create OpenSearch domain with cheapest configuration
        opensearch_domain = opensearch.Domain(
            self,
            "OpenSearchDomain",
            domain_name=domain_name,
            version=opensearch.EngineVersion.OPENSEARCH_2_3,  # Latest stable version
            # Cheapest instance type
            capacity=opensearch.CapacityConfig(
                data_nodes=1,  # Single node (cheapest)
                data_node_instance_type="t3.small.search",  # Smallest instance type
            ),
            # Use EBS storage (cheaper than instance storage for small deployments)
            ebs=opensearch.EbsOptions(
                volume_size=10,  # Minimum 10 GB
                volume_type=ec2.EbsDeviceVolumeType.GP3,  # GP3 is cheaper than GP2
            ),
            # Disable dedicated master nodes (saves cost)
            zone_awareness=opensearch.ZoneAwarenessConfig(enabled=False),
            # Enable encryption at rest (free)
            encryption_at_rest=opensearch.EncryptionAtRestOptions(enabled=True),
            # Restrictive access policy: only this account can call the domain
            access_policies=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.AccountPrincipal(self.account)],
                    actions=["es:ESHttp*", "es:Describe*", "es:List*"],
                    resources=[
                        f"arn:aws:es:{self.region}:{self.account}:domain/{domain_name}",
                        f"arn:aws:es:{self.region}:{self.account}:domain/{domain_name}/*",
                    ],
                )
            ],
            # Node-to-node encryption (free)
            node_to_node_encryption=True,
            # Enforce HTTPS (free)
            enforce_https=True,
            # Removal policy
            removal_policy=RemovalPolicy.DESTROY,
        )

        # S3 Processor for OpenSearch (ingests S3 logs into the domain)
        s3_processor_opensearch_function = _lambda.Function(
            self,
            "S3ProcessorOpenSearchLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../src/lambda/s3_processor_opensearch"),
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "OPENSEARCH_ENDPOINT": opensearch_domain.domain_endpoint,
                "OPENSEARCH_INDEX": "apigw-logs",
            },
        )

        # Reference existing S3 bucket (manual notification required)
        # Configure in S3 console: prefix logs/ -> S3ProcessorOpenSearchLambda
        s3_bucket = s3.Bucket.from_bucket_name(
            self, "ExistingS3BucketForOS", bucket_name="test-nf-tags"
        )

        # Allow S3 to invoke this lambda
        s3_processor_opensearch_function.add_permission(
            "AllowS3InvokeOpenSearch",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            source_arn=f"{s3_bucket.bucket_arn}/*",
            source_account=self.account,
        )

        # Grant read access to the bucket objects
        s3_bucket.grant_read(s3_processor_opensearch_function)

        # Output the domain endpoint
        CfnOutput(
            self,
            "OpenSearchDomainEndpoint",
            value=opensearch_domain.domain_endpoint,
            description="OpenSearch Domain Endpoint",
            export_name="OpenSearchDomainEndpoint",
        )

        # Output the domain ARN
        CfnOutput(
            self,
            "OpenSearchDomainArn",
            value=opensearch_domain.domain_arn,
            description="OpenSearch Domain ARN",
            export_name="OpenSearchDomainArn",
        )
