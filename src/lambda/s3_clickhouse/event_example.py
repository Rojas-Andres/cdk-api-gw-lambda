EVENT = {
    "Records": [
        {
            "eventVersion": "2.1",
            "eventSource": "aws:s3",
            "awsRegion": "us-east-1",
            "eventTime": "2026-01-09T23:25:55.391Z",
            "eventName": "ObjectCreated:Put",
            "userIdentity": {"principalId": "AWS:AROAWLPC4ZKYSZXGRSHW2:andres.rojas"},
            "requestParameters": {"sourceIPAddress": "190.99.139.120"},
            "responseElements": {
                "x-amz-request-id": "HJKZBWKMTYJAJC5Y",
                "x-amz-id-2": "VBjzvHgKZaLWkC36VdPFhoWowNOzXKPwD+2oMGQjFOc/+6idc0pYEQ6wWLrdsJENYAys50Exn+O9GpZu9BjYzBTAYCr7pSb/",
            },
            "s3": {
                "s3SchemaVersion": "1.0",
                "configurationId": "S3BucketNotf",
                "bucket": {
                    "name": "test-nf-tags",
                    "ownerIdentity": {"principalId": "A2XD59ALMM2X7I"},
                    "arn": "arn:aws:s3:::test-nf-tags",
                },
                "object": {
                    "key": "fake_logs.gz",
                    "size": 11548,
                    "eTag": "93bf900e7d9c2f90a4d390360761e868",
                    "sequencer": "0069618E835D5CE7F6",
                },
            },
        }
    ]
}

from dotenv import load_dotenv

load_dotenv()
from handler import handler

handler(EVENT, {})
