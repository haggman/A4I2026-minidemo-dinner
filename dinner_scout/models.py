"""The Gemini models for either backend, so nothing else has to care where Gemini is served from.

On Google Cloud's Agent Platform (the default) there is no Gemini key: google-genai uses Application Default
Credentials (Cloud Shell's own, a Cloud Run service account, or `gcloud auth application-default login` on a
laptop). The Live model is served from the "us" multi-region and the text models from "global", so each model gets
its own client settings; ADK lets a model carry them through `Gemini(client_kwargs=...)`. The SDK's switch for
Agent Platform is still called `vertexai`, the platform's old name.
"""
from google import genai
from google.adk.models import Gemini

from . import config


def client_kwargs(location: str) -> dict:
    if config.ON_AGENT_PLATFORM:
        return {"vertexai": True, "project": config.PROJECT, "location": location}
    return {"vertexai": False, "api_key": config.GEMINI_API_KEY}


def ready() -> tuple[bool, str]:
    """Can we call Gemini at all with the settings in force? (False, why) if not."""
    if config.ON_AGENT_PLATFORM:
        if not config.PROJECT:
            return False, "backend is agent-platform but no project: run `gcloud config set project ID`, then source activate.sh"
        return True, ""
    if not config.GEMINI_API_KEY:
        return False, "backend is gemini-api but GOOGLE_API_KEY is empty in keys.env"
    return True, ""


def live_model() -> Gemini:
    return Gemini(model=config.LIVE_MODEL, client_kwargs=client_kwargs(config.LIVE_LOCATION))


def text_model() -> Gemini:
    return Gemini(model=config.TEXT_MODEL, client_kwargs=client_kwargs(config.TEXT_LOCATION))


def live_client() -> genai.Client:
    return genai.Client(**client_kwargs(config.LIVE_LOCATION))


def text_client() -> genai.Client:
    return genai.Client(**client_kwargs(config.TEXT_LOCATION))
