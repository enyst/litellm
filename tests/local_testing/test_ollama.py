import asyncio
import json
import os
import sys
import traceback

from dotenv import load_dotenv

load_dotenv()
import io
import os

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
from unittest import mock

import pytest

import litellm

## for ollama we can't test making the completion call
from litellm.utils import EmbeddingResponse, get_llm_provider, get_optional_params


def test_get_ollama_params():
    try:
        converted_params = get_optional_params(
            custom_llm_provider="ollama",
            model="llama2",
            max_tokens=20,
            temperature=0.5,
            stream=True,
        )
        print("Converted params", converted_params)
        assert converted_params == {
            "num_predict": 20,
            "stream": True,
            "temperature": 0.5,
        }, f"{converted_params} != {'num_predict': 20, 'stream': True, 'temperature': 0.5}"
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


# test_get_ollama_params()


def test_get_ollama_model():
    try:
        model, custom_llm_provider, _, _ = get_llm_provider("ollama/code-llama-22")
        print("Model", "custom_llm_provider", model, custom_llm_provider)
        assert custom_llm_provider == "ollama", f"{custom_llm_provider} != ollama"
        assert model == "code-llama-22", f"{model} != code-llama-22"
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


# test_get_ollama_model()


def test_ollama_json_mode():
    # assert that format: json gets passed as is to ollama
    try:
        converted_params = get_optional_params(
            custom_llm_provider="ollama", model="llama2", format="json", temperature=0.5
        )
        print("Converted params", converted_params)
        assert converted_params == {
            "temperature": 0.5,
            "format": "json",
            "stream": False,
        }, f"{converted_params} != {'temperature': 0.5, 'format': 'json', 'stream': False}"
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


# test_ollama_json_mode()


def test_ollama_vision_model():
    from litellm.llms.custom_httpx.http_handler import HTTPHandler

    client = HTTPHandler()
    from unittest.mock import patch

    with patch.object(client, "post") as mock_post:
        try:
            litellm.completion(
                model="ollama/llama3.2-vision:11b",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Whats in this image?"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "https://dummyimage.com/100/100/fff&text=Test+image"
                                },
                            },
                        ],
                    }
                ],
                client=client,
            )
        except Exception as e:
            print(e)
        mock_post.assert_called()

        print(mock_post.call_args.kwargs)

        json_data = json.loads(mock_post.call_args.kwargs["data"])
        assert json_data["model"] == "llama3.2-vision:11b"
        assert "images" in json_data
        assert "prompt" in json_data
        assert json_data["prompt"].startswith("### User:\n")


mock_ollama_embedding_response = EmbeddingResponse(model="ollama/nomic-embed-text")


@mock.patch(
    "litellm.llms.ollama.completion.handler.ollama_embeddings",
    return_value=mock_ollama_embedding_response,
)
def test_ollama_embeddings(mock_embeddings):
    # assert that ollama_embeddings is called with the right parameters
    try:
        embeddings = litellm.embedding(
            model="ollama/nomic-embed-text", input=["hello world"]
        )
        print(embeddings)
        mock_embeddings.assert_called_once_with(
            api_base="http://localhost:11434",
            model="nomic-embed-text",
            prompts=["hello world"],
            optional_params=mock.ANY,
            logging_obj=mock.ANY,
            model_response=mock.ANY,
            encoding=mock.ANY,
        )
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


# test_ollama_embeddings()


@mock.patch(
    "litellm.llms.ollama.completion.handler.ollama_aembeddings",
    return_value=mock_ollama_embedding_response,
)
def test_ollama_aembeddings(mock_aembeddings):
    # assert that ollama_aembeddings is called with the right parameters
    try:
        embeddings = asyncio.run(
            litellm.aembedding(model="ollama/nomic-embed-text", input=["hello world"])
        )
        print(embeddings)
        mock_aembeddings.assert_called_once_with(
            api_base="http://localhost:11434",
            model="nomic-embed-text",
            prompts=["hello world"],
            optional_params=mock.ANY,
            logging_obj=mock.ANY,
            model_response=mock.ANY,
            encoding=mock.ANY,
        )
    except Exception as e:
        pytest.fail(f"Error occurred: {e}")


# test_ollama_aembeddings()


@pytest.mark.skip(reason="local only test")
def test_ollama_chat_function_calling():
    import json

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                        },
                    },
                    "required": ["location"],
                },
            },
        },
    ]

    messages = [
        {"role": "user", "content": "What's the weather like in San Francisco?"}
    ]

    response = litellm.completion(
        model="ollama_chat/llama3.1",
        messages=messages,
        tools=tools,
    )
    tool_calls = response.choices[0].message.get("tool_calls", None)

    assert tool_calls is not None

    print(json.loads(tool_calls[0].function.arguments))

    print(response)


def test_ollama_ssl_verify():
    from litellm.llms.custom_httpx.http_handler import HTTPHandler
    import ssl
    import httpx

    try:
        response = litellm.completion(
            model="ollama/llama3.1",
            messages=[
                {
                    "role": "user",
                    "content": "What's the weather like in San Francisco?",
                }
            ],
            ssl_verify=False,
        )
    except Exception as e:
        print(e)

    client: HTTPHandler = litellm.in_memory_llm_clients_cache.get_cache(
        "httpx_clientssl_verify_False"
    )

    test_client = httpx.Client(verify=False)
    print(client)
    assert (
        client.client._transport._pool._ssl_context.verify_mode
        == test_client._transport._pool._ssl_context.verify_mode
    )


@pytest.mark.parametrize("stream", [True, False])
@pytest.mark.asyncio
async def test_async_ollama_ssl_verify(stream):
    from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler
    import httpx

    try:
        response = await litellm.acompletion(
            model="ollama/llama3.1",
            messages=[
                {
                    "role": "user",
                    "content": "What's the weather like in San Francisco?",
                }
            ],
            ssl_verify=False,
            stream=stream,
        )
    except Exception as e:
        print(e)

    client: AsyncHTTPHandler = litellm.in_memory_llm_clients_cache.get_cache(
        "async_httpx_clientssl_verify_Falseollama"
    )

    test_client = httpx.AsyncClient(verify=False)
    print(client)
    assert (
        client.client._transport._pool._ssl_context.verify_mode
        == test_client._transport._pool._ssl_context.verify_mode
    )
