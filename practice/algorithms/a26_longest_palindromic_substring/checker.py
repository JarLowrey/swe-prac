def check(args, expect, actual):
    """Several palindromes can share the longest length ("bab" and "aba" in "baba"), so accept
    any palindromic substring of s that is as long as the reference's answer."""
    (s,) = args
    if not isinstance(actual, str):
        return f"Return a string, not {type(actual).__name__}."
    if actual not in s:
        return f"{actual!r} is not a substring of s."
    if actual != actual[::-1]:
        return f"{actual!r} is not a palindrome."
    if len(actual) < len(expect):
        return (
            f"{actual!r} has length {len(actual)}, but s has a palindrome of length "
            f"{len(expect)}, such as {expect!r}."
        )
    return len(actual) == len(expect)
