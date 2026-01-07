from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_logs as logs,
    aws_iam as iam,
    Duration,
    Tags,
    RemovalPolicy,
)
from constructs import Construct
import os


class LambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add tags to the stack (must comply with SCP policies)
        Tags.of(self).add(
            "Environment", "testing"
        )  # Allowed: testing, prod, sandbox, development, training, poc
        Tags.of(self).add("Owner", "tmd-cloud")  # Must be exactly "tmd-cloud"
        Tags.of(self).add("IsCritical", "true")  # Allowed: true, false
        Tags.of(self).add("IsTemporal", "false")  # Allowed: true, false
        Tags.of(self).add("Project", "cloud-deployments")
        Tags.of(self).add(
            "ProjectName", "cloud-deployments"
        )  # Required by SCP for resource creation
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
        Tags.of(lambda_function).add(
            "ProjectName", "cloud-deployments"
        )  # Required by SCP for lambda:CreateFunction
        Tags.of(lambda_function).add("Repository", "cloud-deployments")

        # Create CloudWatch Log Group for API Gateway
        log_group = logs.LogGroup(
            self,
            "APIGatewayLogGroup",
            log_group_name=f"/aws/apigateway/{self.stack_name}-fastapi",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Apply tags to Log Group
        Tags.of(log_group).add("Environment", "testing")
        Tags.of(log_group).add("Owner", "tmd-cloud")
        Tags.of(log_group).add("IsCritical", "true")
        Tags.of(log_group).add("IsTemporal", "false")
        Tags.of(log_group).add("Project", "cloud-deployments")
        Tags.of(log_group).add("ProjectName", "cloud-deployments")
        Tags.of(log_group).add("Repository", "cloud-deployments")

        # API Gateway REST API with logging enabled
        api = apigateway.RestApi(
            self,
            "FastAPIAPI",
            rest_api_name="FastAPI Lambda API",
            description="API Gateway for FastAPI Lambda function",
            cloud_watch_role=True,  # CDK will create a role automatically
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
                access_log_destination=apigateway.LogGroupLogDestination(log_group),
                access_log_format=apigateway.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=True,
                ),
            ),
        )

        # Integrate Lambda with API Gateway
        lambda_integration = apigateway.LambdaIntegration(
            lambda_function,
            request_templates={"application/json": '{"statusCode": "200"}'},
        )

        # Create specific resource for /user route
        user_resource = api.root.add_resource("user")
        user_resource.add_method("GET", lambda_integration)
