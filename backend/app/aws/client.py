"""
AWS Client Factory and Session Management
"""

import boto3
from botocore.config import Config

from app.core.config import settings


class AWSClientFactory:
    """Factory for creating AWS service clients"""

    def __init__(
        self,
        region_name: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        session_token: str | None = None,
    ):
        """
        Initialize AWS client factory

        Args:
            region_name: AWS region (defaults to settings.AWS_REGION)
            access_key_id: AWS access key (defaults to settings)
            secret_access_key: AWS secret key (defaults to settings)
            session_token: Optional session token for temporary credentials
        """
        self.region_name = region_name or settings.AWS_REGION
        self.access_key_id = access_key_id or settings.AWS_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.AWS_SECRET_ACCESS_KEY
        self.session_token = session_token or settings.AWS_SESSION_TOKEN

        # Boto3 config with retries
        self.config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            region_name=self.region_name,
        )

    def _get_session(self):
        """Create boto3 session"""
        session_kwargs = {
            "region_name": self.region_name,
        }

        if self.access_key_id and self.secret_access_key:
            session_kwargs.update(
                {
                    "aws_access_key_id": self.access_key_id,
                    "aws_secret_access_key": self.secret_access_key,
                }
            )

            if self.session_token:
                session_kwargs["aws_session_token"] = self.session_token

        return boto3.Session(**session_kwargs)

    def get_ec2_client(self):
        """Get EC2 client"""
        session = self._get_session()
        return session.client("ec2", config=self.config)

    def get_cloudwatch_client(self):
        """Get CloudWatch client"""
        session = self._get_session()
        return session.client("cloudwatch", config=self.config)

    def get_pricing_client(self):
        """Get AWS Pricing client"""
        session = self._get_session()
        # Pricing API is only available in us-east-1 and ap-south-1
        pricing_region = (
            "us-east-1" if self.region_name != "ap-south-1" else "ap-south-1"
        )
        return session.client("pricing", region_name=pricing_region, config=self.config)

    def get_ce_client(self):
        """Get Cost Explorer client"""
        session = self._get_session()
        return session.client("ce", config=self.config)


# Global factory instance (can be overridden per request)
default_factory = AWSClientFactory()
