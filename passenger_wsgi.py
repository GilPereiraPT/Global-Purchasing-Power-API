"""EarnWage production entry for CloudLinux Passenger/LiteSpeed.

Native WSGI, like Collexall: avoids the a2wsgi/ASGI blocking observed on
this host. The FastAPI app remains available for other ASGI deployments.
"""
from app.native_wsgi import application
