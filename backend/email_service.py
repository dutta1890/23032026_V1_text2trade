"""Email service using Resend for transactional emails."""
import os
import asyncio
import logging
import resend

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
EMAIL_ENABLED = os.environ.get("EMAIL_ENABLED", "false").lower() == "true"

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


async def send_email(to: str, subject: str, html: str) -> dict:
    """Send an email via Resend. Returns dict with {sent, sandbox_restricted, error}."""
    result = {"sent": False, "sandbox_restricted": False, "error": None}

    if not EMAIL_ENABLED or not RESEND_API_KEY:
        logger.info(f"[EMAIL_DISABLED] to={to} subject={subject}")
        result["error"] = "Email service is disabled"
        return result

    params = {
        "from": SENDER_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    try:
        resp = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL_SENT] to={to} subject={subject} id={resp.get('id', '')}")
        result["sent"] = True
        return result
    except Exception as e:
        error_str = str(e).lower()
        is_sandbox = "testing" in error_str or "sandbox" in error_str or "only send" in error_str or "403" in error_str
        if is_sandbox:
            result["sandbox_restricted"] = True
            result["error"] = "Resend sandbox mode: can only send to the account owner's email"
            logger.warning(f"[EMAIL_SANDBOX] to={to} — sandbox restriction. OTP logged to console.")
        else:
            result["error"] = str(e)
            logger.error(f"[EMAIL_FAILED] to={to} error={e}")
        return result


def otp_email_html(otp: str) -> str:
    return f"""
    <div style="font-family: 'Courier New', monospace; max-width: 480px; margin: 0 auto; padding: 32px; background: #0f0f11; color: #e5e5e5;">
      <div style="border-bottom: 1px solid #2a2a2e; padding-bottom: 16px; margin-bottom: 24px;">
        <span style="color: #00e676; font-weight: bold; font-size: 16px;">Text2trade</span>
      </div>
      <h2 style="font-size: 18px; margin: 0 0 8px; color: #fff;">Password Reset OTP</h2>
      <p style="font-size: 13px; color: #999; margin: 0 0 24px;">Use the code below to reset your password. It expires in 15 minutes.</p>
      <div style="background: #1a1a1e; border: 1px solid #2a2a2e; padding: 20px; text-align: center; margin-bottom: 24px;">
        <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #00e676;">{otp}</span>
      </div>
      <p style="font-size: 11px; color: #666; margin: 0;">If you didn't request this, ignore this email. Your account is safe.</p>
    </div>
    """


def backtest_complete_html(strategy_name: str, symbol: str, pnl_pct: float, win_rate: float, trades: int) -> str:
    pnl_color = "#00e676" if pnl_pct >= 0 else "#ff5252"
    return f"""
    <div style="font-family: 'Courier New', monospace; max-width: 480px; margin: 0 auto; padding: 32px; background: #0f0f11; color: #e5e5e5;">
      <div style="border-bottom: 1px solid #2a2a2e; padding-bottom: 16px; margin-bottom: 24px;">
        <span style="color: #00e676; font-weight: bold; font-size: 16px;">Text2trade</span>
      </div>
      <h2 style="font-size: 18px; margin: 0 0 8px; color: #fff;">Backtest Complete</h2>
      <p style="font-size: 13px; color: #999; margin: 0 0 20px;">Your backtest for <strong style="color: #fff;">{strategy_name}</strong> on {symbol} has finished.</p>
      <div style="background: #1a1a1e; border: 1px solid #2a2a2e; padding: 16px; margin-bottom: 24px;">
        <table style="width: 100%; border-collapse: collapse;">
          <tr>
            <td style="padding: 6px 0; font-size: 11px; color: #999;">P&amp;L</td>
            <td style="padding: 6px 0; font-size: 14px; font-weight: bold; color: {pnl_color}; text-align: right;">{'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; font-size: 11px; color: #999;">Win Rate</td>
            <td style="padding: 6px 0; font-size: 14px; font-weight: bold; color: #fff; text-align: right;">{win_rate:.1f}%</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; font-size: 11px; color: #999;">Total Trades</td>
            <td style="padding: 6px 0; font-size: 14px; font-weight: bold; color: #fff; text-align: right;">{trades}</td>
          </tr>
        </table>
      </div>
      <p style="font-size: 11px; color: #666;">Log in to see full results and equity curve.</p>
    </div>
    """


def alert_triggered_html(alerts: list) -> str:
    rows = ""
    for a in alerts:
        severity_color = "#ff5252" if a.get("severity") == "critical" else "#ffab40"
        rows += f"""
        <tr>
          <td style="padding: 8px; font-size: 12px; color: #fff; border-bottom: 1px solid #2a2a2e;">{a.get('strategy_name', '')}</td>
          <td style="padding: 8px; font-size: 12px; color: {severity_color}; border-bottom: 1px solid #2a2a2e;">{a.get('message', '')}</td>
        </tr>
        """
    return f"""
    <div style="font-family: 'Courier New', monospace; max-width: 480px; margin: 0 auto; padding: 32px; background: #0f0f11; color: #e5e5e5;">
      <div style="border-bottom: 1px solid #2a2a2e; padding-bottom: 16px; margin-bottom: 24px;">
        <span style="color: #00e676; font-weight: bold; font-size: 16px;">Text2trade</span>
      </div>
      <h2 style="font-size: 18px; margin: 0 0 8px; color: #fff;">Alert Triggered</h2>
      <p style="font-size: 13px; color: #999; margin: 0 0 20px;">{len(alerts)} alert(s) need your attention.</p>
      <table style="width: 100%; border-collapse: collapse; background: #1a1a1e; border: 1px solid #2a2a2e;">
        <tr>
          <th style="padding: 8px; font-size: 10px; color: #666; text-align: left; border-bottom: 1px solid #2a2a2e;">STRATEGY</th>
          <th style="padding: 8px; font-size: 10px; color: #666; text-align: left; border-bottom: 1px solid #2a2a2e;">CONDITION</th>
        </tr>
        {rows}
      </table>
      <p style="font-size: 11px; color: #666; margin-top: 16px;">Log in to review and manage your alerts.</p>
    </div>
    """
