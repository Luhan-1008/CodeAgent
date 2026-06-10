from .web import WebChecker
from .checker_pipeline import CheckerPipeline
from .python import SyntaxChecker, ImportChecker, AttributeChecker, PylintChecker


python_checkers = CheckerPipeline()
python_checkers.add_checker(
    SyntaxChecker(),
    ImportChecker(),
    # AttributeChecker(),
    PylintChecker(),
)

web_checkers = CheckerPipeline()
web_checkers.add_checker(WebChecker())
