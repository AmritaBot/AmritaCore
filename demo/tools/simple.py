from amrita_core import simple_tool


@simple_tool
def add(a: int, b: int) -> int:
    """Add number

    Args:
        a (int): First number
        b (int): Second number

    Returns:
        int: Return the final value
    """
    return a + b
