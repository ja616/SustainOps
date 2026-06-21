import boto3
import json
from app.core.config import settings


class BedrockModel:
    """
    Real AWS Bedrock model abstraction.
    Supports Amazon Nova Lite (primary) and Nova Pro.
    Uses the Converse API which works uniformly across all Bedrock models.
    """

    def __init__(self, model_id: str = None, region_name: str = None):
        self.model_id = model_id or settings.BEDROCK_MODEL_ID
        self.region_name = region_name or settings.AWS_DEFAULT_REGION
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=self.region_name,
        )

    def generate(self, prompt: str, system: str = "") -> str:
        """
        Calls Bedrock Converse API. Works for Nova Lite, Nova Pro, and Claude.
        """
        messages = [{"role": "user", "content": [{"text": prompt}]}]

        kwargs = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": 2048,
                "temperature": 0.1,
            },
        }

        if system:
            kwargs["system"] = [{"text": system}]

        try:
            response = self.client.converse(**kwargs)
            return response["output"]["message"]["content"][0]["text"]
        except Exception as e:
            raise RuntimeError(f"Bedrock call failed for model {self.model_id}: {e}")
