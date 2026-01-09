EVENT = {
    "Records": [
        {
            "eventVersion": "2.1",
            "eventSource": "aws:s3",
            "awsRegion": "us-east-1",
            "eventTime": "2026-01-08T20:57:09.449Z",
            "eventName": "ObjectCreated:Put",
            "userIdentity": {"principalId": "AWS:AROAWLPC4ZKYSZXGRSHW2:andres.rojas"},
            "requestParameters": {"sourceIPAddress": "190.99.139.120"},
            "responseElements": {
                "x-amz-request-id": "XNDP9SJ5016JFTT4",
                "x-amz-id-2": "x/WFWXKHA1gPaLbUiu/rOT6ELRxEWFWZDaSHCzXspPo77RgJ8PLFLNMGt7UqLFhR4iIQf56WpDpCL1/iKjS33wszFIc7BXwv",
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
                    "key": "logs/year%3D2026/month%3D01/day%3D08/PUT-S3-9V45m-4-2026-01-08-19-33-59-d26baa70-91ee-444e-9cf2-0855447481de_v2.gz",
                    "size": 10079,
                    "eTag": "036c56cd49d006c13720a095c3036dd1",
                    "sequencer": "0069601A256BF73578",
                },
            },
        }
    ]
}

from dotenv import load_dotenv

load_dotenv()
from handler import handler

handler(EVENT, {})
