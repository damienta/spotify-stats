import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def aws(monkeypatch):
    """Fake AWS (moto) in eu-north-1 with the project's bucket and tables."""
    for name in ("AWS_PROFILE", "AWS_DEFAULT_PROFILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-north-1")
    with mock_aws():
        s3 = boto3.client("s3")
        s3.create_bucket(
            Bucket="data", CreateBucketConfiguration={"LocationConstraint": "eu-north-1"}
        )
        dynamodb = boto3.resource("dynamodb")
        dynamodb.create_table(
            TableName="users",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName="stats",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "stat_name", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "stat_name", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield
