import shutil
from pathlib import Path

# Requires "ssl-cert" package
CERTIFICATE_PATH = "/etc/ssl/certs/ssl-cert-snakeoil.pem"
KEY_PATH = "/etc/ssl/private/ssl-cert-snakeoil.key"

SSL_FOLDER = Path(__file__).parent / "ssl"
SSL_FOLDER.mkdir(exist_ok=True)

shutil.copy(CERTIFICATE_PATH, SSL_FOLDER / "cert.pem")
shutil.copy(KEY_PATH, SSL_FOLDER / "privkey.pem")

# The web server runs as an unprivileged user (uid 101), which must be able to
# read the mounted key. Acceptable for this self-signed example key only.
(SSL_FOLDER / "privkey.pem").chmod(0o644)
