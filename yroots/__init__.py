#Do not delete this file. It tells python that YRoots is a module you
#can import from. Public facing functions should be imported here so
#they can be used directly.
name = "yroots"
from .subdivision import solve
from .polyroots import solve as polysolve
from .polynomial import MultiPower
from .polynomial import MultiCheb
