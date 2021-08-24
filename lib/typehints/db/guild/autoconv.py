from typing import TypedDict, Literal

__all__: tuple = ('AutomaticConversion',)


class AutomaticConversion(TypedDict):
    codeblock: bool
    gh_lines: bool
    gh_lines: Literal[0, 1, 2]
