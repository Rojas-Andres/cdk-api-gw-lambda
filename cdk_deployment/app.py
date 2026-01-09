#!/usr/bin/env python3
import os
import aws_cdk as cdk
from lambda_stack import LambdaStack
from opensearch_stack import OpenSearchStack

app = cdk.App()

LambdaStack(
    app,
    "LambdaStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)

OpenSearchStack(
    app,
    "OpenSearchStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)

app.synth()
