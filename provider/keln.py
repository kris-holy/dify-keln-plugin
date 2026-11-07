from collections.abc import Mapping

from dify_plugin import ModelProvider
from dify_plugin.entities.model import ModelType

# GET /v1/models is public and accepts any key, so checking a key takes a short chat request.
VALIDATION_MODEL = "zai-org/glm-5.3"


class KelnModelProvider(ModelProvider):
    def validate_provider_credentials(self, credentials: Mapping) -> None:
        llm = self.get_model_instance(ModelType.LLM)
        llm.validate_credentials(model=VALIDATION_MODEL, credentials=dict(credentials))
