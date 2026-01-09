from aws_cdk import (
    Stack,
    aws_opensearchservice as opensearch,
    aws_ec2 as ec2,
    Tags,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct
import os


class OpenSearchStack(Stack):
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

        # Create OpenSearch domain with cheapest configuration
        opensearch_domain = opensearch.Domain(
            self,
            "OpenSearchDomain",
            domain_name="test-opensearch-domain",
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
            encryption=opensearch.EncryptionConfig(
                encryption_at_rest=opensearch.EncryptionAtRestOptions(enabled=True)
            ),
            # Basic access control (cheaper than fine-grained)
            access_policies=[
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "es:*",
                    "Resource": "*",
                }
            ],
            # Node-to-node encryption (free)
            node_to_node_encryption=True,
            # Enforce HTTPS (free)
            enforce_https=True,
            # Removal policy
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Output the domain endpoint
        CfnOutput(
            self,
            "OpenSearchDomainEndpoint",
            value=opensearch_domain.domain_endpoint,
            description="OpenSearch Domain Endpoint",
        )

        # Output the domain ARN
        CfnOutput(
            self,
            "OpenSearchDomainArn",
            value=opensearch_domain.domain_arn,
            description="OpenSearch Domain ARN",
        )
