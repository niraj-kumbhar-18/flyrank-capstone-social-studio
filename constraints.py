import re

CONSTRAINT_PROFILES = {
    "mock_x": {
        "max_length": 280,
        "tone": "short, punchy",
        "max_hashtags": 2,
    },
    "mock_linkedin": {
        "max_length": 3000,
        "tone": "professional",
        "max_hashtags": 3,
    },
    "telegram": {
        "max_length": 1024,
        "tone": "casual, informative",
        "max_hashtags": 3,
    },
}


def validate_variant(platform: str, content: str) -> list[str]:
    if platform not in CONSTRAINT_PROFILES:
        return [f"Unsupported platform: {platform}"]

    profile = CONSTRAINT_PROFILES[platform]
    errors = []

    if not content.strip():
        errors.append("Content cannot be empty")
        
    if len(content) > profile["max_length"]:
        errors.append(
            f"Content exceeds the {profile['max_length']} character limit"
        )

    hashtags = re.findall(r"#\w+", content)

    if len(hashtags) > profile["max_hashtags"]:
        errors.append(
            f"Content contains more than {profile['max_hashtags']} hashtags"
        )

    return errors