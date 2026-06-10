def format_cost(cost: float) -> str:
    """
    Format cost to keep only the first non-zero digit after the decimal point.

    Examples:
        ```
        0.00000123 -> 0.000001
        0.123456 -> 0.1
        10.321 -> 10.3
        ```

    Args:
        cost (float): The cost value to format

    Returns:
        Formatted cost as a string
    """
    if cost == 0:
        return "0"

    # Convert to string in scientific notation
    sci_notation = f"{cost:.10e}"
    mantissa, exponent = sci_notation.split("e")
    mantissa = float(mantissa)
    exponent = int(exponent)

    # Find the first significant digit after decimal
    if exponent < 0:
        # For numbers less than 1
        precision = abs(exponent)
        return f"{cost:.{precision}f}"
    else:
        # For numbers >= 1
        # Keep only first digit after decimal
        return f"{cost:.1f}"
