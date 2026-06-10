import base64


def generate_image_message(image_path: str, str_message: str) -> str:
    """
    Generate a message with an image.

    Args:
        image_path (str): The path to the image.
        str_message (str): The message to be sent.

    Returns:
        str: The message of OpenAI API format, with base64 encoded image.
    """
    with open(image_path, "rb") as f:
        image = f.read()
    base64_image = base64.b64encode(image).decode("utf-8")
    base64_image = f"data:image/jpeg;base64,{base64_image}"

    message = {
        "role": "user",
        "content": [
            {"type": "text", "text": str_message},
            {"type": "image_url", "image_url": {"url": base64_image}},
        ],
    }

    return message
