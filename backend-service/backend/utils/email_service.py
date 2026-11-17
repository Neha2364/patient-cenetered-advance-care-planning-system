import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app
from backend.config import Config

logger = logging.getLogger(__name__)


def is_email_configured() -> bool:
    """Check whether the SMTP email service is configured.
    
    Returns True only if SMTP_HOST is non-empty.
    """
    host = ""
    try:
        if current_app:
            host = current_app.config.get('SMTP_HOST') or getattr(Config, 'SMTP_HOST', '')
    except Exception:
        host = getattr(Config, 'SMTP_HOST', '')
    return bool(host and str(host).strip())


def send_password_reset_email(
    to_email: str,
    recipient_name: str,
    reset_link: str,
    expires_in_minutes: int = 60
) -> tuple[bool, str]:
    """Send a secure password reset email to a doctor.
    
    Returns (True, message) on success or (False, error_message) on failure.
    """
    if not is_email_configured():
        return False, (
            "Email delivery service is currently not configured on this server. "
            "Please contact your administrator to reset your password or configure SMTP settings."
        )

    try:
        cfg = current_app.config if current_app else {}
    except Exception:
        cfg = {}

    sender = cfg.get('SMTP_FROM') or getattr(Config, 'SMTP_FROM', 'noreply@acpcare.app') or 'noreply@acpcare.app'
    display_name = recipient_name.strip() if recipient_name else "Doctor"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "ACP Care — Reset Your Doctor Portal Password"
    msg["From"] = f"ACP Care <{sender}>"
    msg["To"] = to_email

    # Plain text version
    text_content = f"""Hello Dr. {display_name},

We received a request to reset the password for your ACP Care Doctor Portal account ({to_email}).

To choose a new password, please visit the following link:
{reset_link}

This link is time-limited and will expire in {expires_in_minutes} minutes. For security, this link can only be used once.

If you did not request a password reset, please ignore this email or notify your system administrator immediately.

Best regards,
ACP Care Clinical Support Team
"""

    # HTML version
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Reset Your Doctor Portal Password</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #1e293b;
      background-color: #f8fafc;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 600px;
      margin: 24px auto;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
    }}
    .header {{
      background: linear-gradient(135deg, #0d9488 0%, #0284c7 100%);
      color: #ffffff;
      padding: 32px 28px;
      text-align: center;
    }}
    .header h1 {{
      margin: 0;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    .header p {{
      margin: 6px 0 0;
      font-size: 13px;
      opacity: 0.9;
    }}
    .content {{
      padding: 32px 28px;
    }}
    .greeting {{
      font-size: 16px;
      font-weight: 600;
      color: #0f172a;
      margin-bottom: 12px;
    }}
    .btn-container {{
      text-align: center;
      margin: 28px 0;
    }}
    .btn {{
      display: inline-block;
      background-color: #0d9488;
      color: #ffffff !important;
      text-decoration: none;
      font-weight: 600;
      font-size: 15px;
      padding: 13px 32px;
      border-radius: 10px;
      box-shadow: 0 4px 8px rgba(13, 148, 136, 0.25);
    }}
    .security-note {{
      background-color: #f1f5f9;
      border-left: 4px solid #0284c7;
      padding: 14px 16px;
      border-radius: 6px;
      font-size: 13px;
      color: #475569;
      margin: 24px 0 16px;
    }}
    .fallback-url {{
      font-size: 12px;
      color: #64748b;
      word-break: break-all;
      margin-top: 16px;
    }}
    .footer {{
      border-top: 1px solid #e2e8f0;
      padding: 20px 28px;
      text-align: center;
      font-size: 12px;
      color: #94a3b8;
      background-color: #f8fafc;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>ACP Care</h1>
      <p>Clinician Portal &bull; Advance Care Planning</p>
    </div>
    <div class="content">
      <div class="greeting">Hello Dr. {display_name},</div>
      <p>
        We received a request to reset the password for your ACP Care Doctor Portal account (<strong>{to_email}</strong>).
      </p>
      <div class="btn-container">
        <a href="{reset_link}" class="btn" target="_blank">Reset Doctor Password</a>
      </div>
      <div class="security-note">
        <strong>Security Notice:</strong>
        <br>
        This link is single-use and will expire in <strong>{expires_in_minutes} minutes</strong>. If you did not initiate this request, no action is needed — your account remains completely secure.
      </div>
      <p class="fallback-url">
        If the button above does not work, copy and paste this link into your browser:
        <br>
        <a href="{reset_link}" style="color: #0d9488;">{reset_link}</a>
      </p>
    </div>
    <div class="footer">
      &copy; ACP Care System. Confidential Clinician Communication.
    </div>
  </div>
</body>
</html>
"""

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        host = cfg.get('SMTP_HOST') or getattr(Config, 'SMTP_HOST', '')
        port = int(cfg.get('SMTP_PORT') or getattr(Config, 'SMTP_PORT', 587) or 587)
        user = cfg.get('SMTP_USER') or getattr(Config, 'SMTP_USER', '')
        password = cfg.get('SMTP_PASSWORD') or getattr(Config, 'SMTP_PASSWORD', '')
        use_tls = cfg.get('SMTP_USE_TLS', getattr(Config, 'SMTP_USE_TLS', True))

        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            if use_tls:
                server.starttls()

        if user and password:
            server.login(user, password)

        server.sendmail(sender, [to_email], msg.as_string())
        server.quit()
        return True, "Password reset email sent successfully."
    except Exception as exc:
        logger.exception("Failed to send password reset email to %s", to_email)
        return False, f"Failed to send email: {str(exc)}"
