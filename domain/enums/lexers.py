from enum import Enum

from pygments import lexers


class Lexers(Enum):
    textn = lexers.TextLexer
    python = lexers.PythonLexer
    javascript = lexers.JavascriptLexer
    html = lexers.HtmlLexer
    bash = lexers.BashLexer
    json = lexers.JsonLexer
    css = lexers.CssLexer
