"""
Authority-specific resource provider implementations.

Each provider knows where to search for educational resources
that support a specific standards authority's learning objectives.
"""

# Import all providers to trigger registration
from . import texas
from . import florida
from . import california
from . import common_core
from . import ib
from . import cambridge
from . import college_board
from . import act
