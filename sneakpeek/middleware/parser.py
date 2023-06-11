import re
from dataclasses import dataclass

from sneakpeek.middleware.base import BaseMiddleware


@dataclass
class RegexMatch:
    """Regex match"""

    full_match: str  #: Full regular expression match
    groups: dict[str, str]  #: Regular expression group matches


class ParserMiddleware(BaseMiddleware):
    """Parser middleware provides parsing utilities"""

    @property
    def name(self) -> str:
        return "parser"

    def regex(
        self,
        text: str,
        pattern: str,
        flags: re.RegexFlag = re.UNICODE | re.MULTILINE | re.IGNORECASE,
    ) -> list[RegexMatch]:
        """Find matches in the text using regular expression

        Args:
            text (str): Text to search in
            pattern (str): Regular expression
            flags (re.RegexFlag, optional): Regular expression flags. Defaults to re.UNICODE | re.MULTILINE | re.IGNORECASE.

        Returns:
            list[RegexMatch]: Matches found in the text
        """
        return [
            RegexMatch(full_match=match.group(0), groups=match.groupdict())
            for match in re.finditer(pattern, text, flags)
        ]
