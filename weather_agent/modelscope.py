import json as json_module
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CHAT_COMPLETIONS_URL = "https://api-inference.modelscope.cn/v1/chat/completions"
DEFAULT_MODEL = "Qwen/Qwen3.5-27B"


class ModelScopeError(RuntimeError):
    """Raised when ModelScope cannot return a valid structured completion."""


class ModelScopeContentError(ModelScopeError):
    """Raised when ModelScope returns content that is not a JSON object."""


class _UrlLibResponse:
    def __init__(self, response):
        self._response = response

    def raise_for_status(self):
        return None

    def json(self):
        return json_module.loads(self._response.read().decode("utf-8"))


class _UrlLibSession:
    def post(self, url, *, json, headers, timeout):
        request = Request(
            url,
            data=json_module.dumps(json).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            return _UrlLibResponse(urlopen(request, timeout=timeout))
        except HTTPError as exc:
            raise ModelScopeError(f"ModelScope HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise ModelScopeError("ModelScope request failed") from exc


class ModelScopeClient:
    def __init__(self, access_token, *, session=None, model=DEFAULT_MODEL):
        self.access_token = access_token
        self.session = session or _UrlLibSession()
        self.model = model

    @classmethod
    def from_environment(cls, *, session=None, model=DEFAULT_MODEL):
        access_token = os.environ.get("MODELSCOPE_ACCESS_TOKEN")
        if not access_token:
            raise ModelScopeError("MODELSCOPE_ACCESS_TOKEN is required")
        return cls(access_token, session=session, model=model)

    def complete_json(self, messages):
        response = self.session.post(
            CHAT_COMPLETIONS_URL,
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 500,
                "response_format": {"type": "json_object"},
            },
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        response.raise_for_status()
        try:
            content = response.json()["choices"][0]["message"]["content"]
            result = json_module.loads(content)
        except (KeyError, IndexError, TypeError, json_module.JSONDecodeError) as exc:
            raise ModelScopeContentError(
                "ModelScope did not return valid JSON content"
            ) from exc
        if not isinstance(result, dict):
            raise ModelScopeContentError("ModelScope JSON content must be an object")
        return result
