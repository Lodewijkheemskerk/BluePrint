"""
TradingView webhook receiver endpoint.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import WebhookAlert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

# Store received webhooks in memory (last 100)
_webhook_history = []
MAX_WEBHOOK_HISTORY = 100


@router.post("/tradingview")
async def receive_tradingview_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive a webhook alert from TradingView.
    TradingView sends a POST with the alert message in the body.
    """
    try:
        content_type = request.headers.get("content-type", "")
        if "json" in content_type:
            body = await request.json()
        else:
            raw = await request.body()
            body = {"message": raw.decode("utf-8")}

        alert = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "source": "tradingview",
            **body,
        }

        _webhook_history.insert(0, alert)
        if len(_webhook_history) > MAX_WEBHOOK_HISTORY:
            _webhook_history.pop()

        logger.info(f"TradingView webhook received: {body}")

        return {"status": "ok", "message": "Webhook received"}

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/tradingview/history")
def get_webhook_history():
    """Get recent TradingView webhook alerts."""
    return _webhook_history


@router.get("/tradingview/test")
def test_webhook():
    """Test endpoint to verify webhook URL is reachable."""
    return {"status": "ok", "message": "Webhook endpoint is active"}
