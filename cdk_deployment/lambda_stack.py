from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_logs as logs,
    aws_logs_destinations as logs_destinations,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
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

        # API Lambda function (FastAPI)
        api_lambda_function = _lambda.Function(
            self,
            "FastAPILambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../src/lambda/api_handler"),
            timeout=Duration.seconds(30),
            memory_size=256,
        )

        # Apply tags directly to API Lambda function (required by SCP)
        Tags.of(api_lambda_function).add("Environment", "testing")
        Tags.of(api_lambda_function).add("Owner", "tmd-cloud")
        Tags.of(api_lambda_function).add("IsCritical", "true")
        Tags.of(api_lambda_function).add("IsTemporal", "false")
        Tags.of(api_lambda_function).add("Project", "cloud-deployments")
        Tags.of(api_lambda_function).add(
            "ProjectName", "cloud-deployments"
        )  # Required by SCP for lambda:CreateFunction
        Tags.of(api_lambda_function).add("Repository", "cloud-deployments")

        # AWS Lambda Powertools Layer (public layer from AWS)
        # ARN format: arn:aws:lambda:{region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:{version}
        powertools_layer = _lambda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            layer_version_arn=f"arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:2",
        )

        # Log Processor Lambda function
        log_processor_function = _lambda.Function(
            self,
            "LogProcessorLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../src/lambda/log_processor"),
            timeout=Duration.seconds(60),
            memory_size=256,
            layers=[powertools_layer],
        )

        # Apply tags directly to Log Processor Lambda function (required by SCP)
        Tags.of(log_processor_function).add("Environment", "testing")
        Tags.of(log_processor_function).add("Owner", "tmd-cloud")
        Tags.of(log_processor_function).add("IsCritical", "true")
        Tags.of(log_processor_function).add("IsTemporal", "false")
        Tags.of(log_processor_function).add("Project", "cloud-deployments")
        Tags.of(log_processor_function).add(
            "ProjectName", "cloud-deployments"
        )  # Required by SCP for lambda:CreateFunction
        Tags.of(log_processor_function).add("Repository", "cloud-deployments")

        # Kinesis Transformer Lambda function (for Firehose to Loki)
        kinesis_transformer_function = _lambda.Function(
            self,
            "KinesisTransformerLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../src/lambda/kinesis_transformer"),
            timeout=Duration.seconds(60),
            memory_size=256,
        )

        # Apply tags directly to Kinesis Transformer Lambda function (required by SCP)
        Tags.of(kinesis_transformer_function).add("Environment", "testing")
        Tags.of(kinesis_transformer_function).add("Owner", "tmd-cloud")
        Tags.of(kinesis_transformer_function).add("IsCritical", "true")
        Tags.of(kinesis_transformer_function).add("IsTemporal", "false")
        Tags.of(kinesis_transformer_function).add("Project", "cloud-deployments")
        Tags.of(kinesis_transformer_function).add(
            "ProjectName", "cloud-deployments"
        )  # Required by SCP for lambda:CreateFunction
        Tags.of(kinesis_transformer_function).add("Repository", "cloud-deployments")

        # S3 Processor Lambda function (triggered by S3 uploads)
        s3_processor_function = _lambda.Function(
            self,
            "S3ProcessorLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../src/lambda/s3_processor"),
            timeout=Duration.seconds(60),
            memory_size=256,
        )

        # Apply tags directly to S3 Processor Lambda function (required by SCP)
        Tags.of(s3_processor_function).add("Environment", "testing")
        Tags.of(s3_processor_function).add("Owner", "tmd-cloud")
        Tags.of(s3_processor_function).add("IsCritical", "true")
        Tags.of(s3_processor_function).add("IsTemporal", "false")
        Tags.of(s3_processor_function).add("Project", "cloud-deployments")
        Tags.of(s3_processor_function).add(
            "ProjectName", "cloud-deployments"
        )  # Required by SCP for lambda:CreateFunction
        Tags.of(s3_processor_function).add("Repository", "cloud-deployments")

        # Reference existing S3 bucket
        # NOTE: CDK cannot add event notifications to existing buckets automatically.
        # You need to configure the S3 event notification manually:
        # 1. Go to S3 Console → test-nf-tags → Properties → Event notifications
        # 2. Create notification:
        #    - Event types: All object create events
        #    - Prefix: logs/
        #    - Destination: Lambda function → S3ProcessorLambda

        s3_bucket = s3.Bucket.from_bucket_name(
            self, "ExistingS3Bucket", bucket_name="test-nf-tags"
        )

        # Grant the lambda permission to be invoked by S3
        s3_processor_function.add_permission(
            "AllowS3Invoke",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            source_arn=s3_bucket.bucket_arn,
        )

        # Grant the lambda permission to read from the S3 bucket
        s3_bucket.grant_read(s3_processor_function)

        # Create CloudWatch Log Group for API Gateway
        log_group = logs.LogGroup(
            self,
            "APIGatewayLogGroup",
            log_group_name=f"/aws/apigateway/{self.stack_name}-fastapi",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

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
            api_lambda_function,
            request_templates={"application/json": '{"statusCode": "200"}'},
        )

        # Create specific resource for /user route
        user_resource = api.root.add_resource("user")
        user_resource.add_method("GET", lambda_integration)

        # Create subscription filter to send logs to Lambda
        log_group.add_subscription_filter(
            "LogProcessorSubscriptionFilter",
            destination=logs_destinations.LambdaDestination(log_processor_function),
            filter_pattern=logs.FilterPattern.all_events(),
        )
