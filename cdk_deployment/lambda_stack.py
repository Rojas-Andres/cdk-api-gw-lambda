from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    Duration,
    Tags,
)
from constructs import Construct
import os


class LambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add tags to the stack (must comply with SCP policies)
        Tags.of(self).add("Environment", "testing")  # Allowed: testing, prod, sandbox, development, training, poc
        Tags.of(self).add("Owner", "tmd-cloud")  # Must be exactly "tmd-cloud"
        Tags.of(self).add("IsCritical", "true")  # Allowed: true, false
        Tags.of(self).add("IsTemporal", "false")  # Allowed: true, false
        Tags.of(self).add("Project", "cloud-deployments")
        Tags.of(self).add("Repository", "cloud-deployments")

        # Lambda function
        lambda_function = _lambda.Function(
            self,
            "FastAPILambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_handler.handler",
            code=_lambda.Code.from_asset("../src"),
            timeout=Duration.seconds(30),
            memory_size=256,
        )

        # Apply tags directly to Lambda function (required by SCP)
        Tags.of(lambda_function).add("Environment", "testing")
        Tags.of(lambda_function).add("Owner", "tmd-cloud")
        Tags.of(lambda_function).add("IsCritical", "true")
        Tags.of(lambda_function).add("IsTemporal", "false")
        Tags.of(lambda_function).add("Project", "cloud-deployments")
        Tags.of(lambda_function).add("Repository", "cloud-deployments")

        # API Gateway REST API
        api = apigateway.RestApi(
            self,
            "FastAPIAPI",
            rest_api_name="FastAPI Lambda API",
            description="API Gateway for FastAPI Lambda function",
        )

        # Integrate Lambda with API Gateway
        lambda_integration = apigateway.LambdaIntegration(
            lambda_function,
            request_templates={"application/json": '{"statusCode": "200"}'},
        )

        # Create specific resource for /user route
        user_resource = api.root.add_resource("user")
        user_resource.add_method("GET", lambda_integration)
