"""Validate HTML content in a file."""

from bs4 import BeautifulSoup
from collections import defaultdict


def is_valid_html(content: str) -> tuple[bool, int, int, str]:
    """
    Validates whether the content at the given file path is valid HTML.

    Args:
        content (str): Content of the file to validate.

    Returns:
        tuple[bool, int, int, str]: A tuple containing:
            - bool: True if the HTML is valid, False otherwise
            - int: The line number of the error (if any)
            - int: The column number of the error (if any)
            - str: The error message (if any)
    """
    if not content.strip():
        return False, None, None, "Empty file"

    soup = BeautifulSoup(content, "html.parser")

    # Check basic HTML structure requirements
    html_tag = soup.find("html")
    if not html_tag:
        return False, None, None, "No <html> tag found"

    # Check for head and body tags
    head_tag = soup.find("head")
    if not head_tag:
        return (False, None, None, "Missing <head> tag")
    body_tag = soup.find("body")
    if not body_tag:
        return (False, None, None, "Missing <body> tag")

    # Check for unclosed tags
    unclosed_tag_error = check_for_unclosed_tags(content)
    if unclosed_tag_error[0] is False:
        return unclosed_tag_error

    # If no errors found
    return (True, None, None, None)


def check_for_unclosed_tags(content: str) -> tuple[bool, int, int, str]:
    """
    Check for unclosed tags in HTML content.

    Args:
        content (str): HTML content to check

    Returns:
        tuple[bool, int, int, str]: A tuple containing:
            - bool: True if no unclosed tags, False otherwise
            - int: The line number of the error (if any)
            - int: The column number of the error (if any)
            - str: The error message (if any)
    """
    soup = BeautifulSoup(content, "html.parser")
    all_tags = soup.find_all()
    open_tags = defaultdict(int)
    unclosed_tags = set()

    for tag in all_tags:
        open_tags[tag.name] += 1

    for tag_name in open_tags:
        opening_count = content.count(f"<{tag_name}")
        closing_count = content.count(f"</{tag_name}")
        if opening_count > closing_count:
            unclosed_tags.add(tag_name)
    if unclosed_tags:
        return (False, None, None, f"Unclosed HTML tag: {', '.join(unclosed_tags)}")

    # No unclosed tags found
    return (True, None, None, None)
