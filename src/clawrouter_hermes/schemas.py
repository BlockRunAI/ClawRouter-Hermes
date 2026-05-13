"""JSON schemas describing the ClawRouter tools to the LLM."""

from __future__ import annotations

IMAGE_GENERATE: dict = {
    "name": "clawrouter_image_generate",
    "description": (
        "Generate an image from a text prompt via ClawRouter. Routes to "
        "google/nano-banana (default), openai/dall-e-3, openai/gpt-image-1, "
        "black-forest/flux-1.1-pro, xai/grok-imagine-image, or zai/cogview-4. "
        "Returns a local proxy URL like http://127.0.0.1:8402/images/<file>.png. "
        "Billed in USDC via x402."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text prompt describing the desired image.",
            },
            "model": {
                "type": "string",
                "description": (
                    "Full model ID. Examples: 'google/nano-banana' (default), "
                    "'openai/dall-e-3', 'openai/gpt-image-1', "
                    "'black-forest/flux-1.1-pro', 'xai/grok-imagine-image'."
                ),
            },
            "size": {
                "type": "string",
                "description": "Image size, e.g. '1024x1024', '1792x1024', '4096x4096'.",
            },
            "n": {
                "type": "integer",
                "description": "Number of images to generate (default 1, max 4).",
                "minimum": 1,
                "maximum": 4,
            },
        },
        "required": ["prompt"],
    },
}

VIDEO_GENERATE: dict = {
    "name": "clawrouter_video_generate",
    "description": (
        "Generate a 5–10 second video via ClawRouter. Models: "
        "bytedance/seedance-1.5-pro (default, cheapest), bytedance/seedance-2.0-fast, "
        "bytedance/seedance-2.0, xai/grok-imagine-video. Async — upstream polling "
        "takes 30–120 seconds. Returns a local proxy URL like "
        "http://127.0.0.1:8402/videos/<file>.mp4. Billed in USDC via x402."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text prompt describing the video.",
            },
            "model": {
                "type": "string",
                "description": (
                    "Full model ID. Default: 'bytedance/seedance-1.5-pro'."
                ),
            },
            "duration": {
                "type": "integer",
                "description": "Video duration in seconds (5 or 10). Model-dependent.",
            },
            "resolution": {
                "type": "string",
                "description": "Resolution string, e.g. '720p', '1080p'. Model-dependent.",
            },
        },
        "required": ["prompt"],
    },
}

WEB_SEARCH: dict = {
    "name": "clawrouter_web_search",
    "description": (
        "Web search via ClawRouter's Exa-powered endpoint. Returns ranked "
        "results with titles, URLs, snippets, and optional full-text content. "
        "Billed in USDC via x402."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language search query.",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default 5, max 20).",
                "minimum": 1,
                "maximum": 20,
            },
            "include_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Restrict results to these domains.",
            },
            "exclude_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Exclude results from these domains.",
            },
            "include_text": {
                "type": "boolean",
                "description": "If true, include full extracted text for each result.",
            },
        },
        "required": ["query"],
    },
}
