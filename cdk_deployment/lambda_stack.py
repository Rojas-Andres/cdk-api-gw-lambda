from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    Duration,
)
from constructs import Construct
import os


class LambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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
