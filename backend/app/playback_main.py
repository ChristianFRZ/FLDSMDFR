from app.core.service_app import service_app
from app.modules.analytics.public import refresh_aggregates
from app.modules.analytics.routes import router as analytics
from app.modules.playback.routes import router as playback

app = service_app("playback", (playback, analytics), jobs=[("agregados", 2, refresh_aggregates)])
