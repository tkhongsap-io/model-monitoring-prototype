#!/usr/bin/env bash
# Make (or reuse) the private CA of the GCP test host and issue the nginx server certificate.
# Run on the VM as root. Run again to renew the server certificate; the root CA is kept.
#
#   sudo ./make-private-ca.sh <internal-ip> [private-dns-name]
#
# Runbook: README.md in this folder.
set -euo pipefail

IP="${1:?usage: make-private-ca.sh <internal-ip> [private-dns-name]}"
DNS_NAME="${2:-}"
CA_DIR="${CA_DIR:-/etc/monitor-test-ca}"
TLS_DIR="${TLS_DIR:-/etc/nginx/tls/test-host}"
ROOT_DAYS="${ROOT_DAYS:-730}"
SERVER_DAYS="${SERVER_DAYS:-90}"

umask 077
install -d -m 755 "$CA_DIR"
install -d -m 755 "$TLS_DIR"

if [[ ! -f "$CA_DIR/root.key" ]]; then
  echo "Making a new root CA in $CA_DIR (valid $ROOT_DAYS days)"
  openssl req -x509 -newkey rsa:4096 -sha256 -days "$ROOT_DAYS" -noenc \
    -keyout "$CA_DIR/root.key" -out "$CA_DIR/root.crt" \
    -subj "/CN=Model Monitor Test Host Root CA" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"
else
  echo "Reusing the root CA in $CA_DIR"
fi
chmod 600 "$CA_DIR/root.key"
chmod 644 "$CA_DIR/root.crt"

SAN="IP:$IP,DNS:localhost,IP:127.0.0.1"
CN="$IP"
if [[ -n "$DNS_NAME" ]]; then
  SAN="DNS:$DNS_NAME,$SAN"
  CN="$DNS_NAME"
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cat > "$WORK/server.ext" <<EOF
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=$SAN
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
EOF

openssl req -new -newkey rsa:2048 -noenc \
  -keyout "$WORK/server.key" -out "$WORK/server.csr" -subj "/CN=$CN"
openssl x509 -req -sha256 -days "$SERVER_DAYS" \
  -in "$WORK/server.csr" -CA "$CA_DIR/root.crt" -CAkey "$CA_DIR/root.key" \
  -CAcreateserial -CAserial "$CA_DIR/root.srl" \
  -extfile "$WORK/server.ext" -out "$WORK/server.crt"

openssl verify -CAfile "$CA_DIR/root.crt" "$WORK/server.crt"

install -m 644 "$WORK/server.crt" "$TLS_DIR/server.crt"
install -m 600 "$WORK/server.key" "$TLS_DIR/server.key"

echo "Server certificate: $TLS_DIR/server.crt (SAN $SAN, valid $SERVER_DAYS days)"
openssl x509 -in "$TLS_DIR/server.crt" -noout -enddate
echo "Clients trust: $CA_DIR/root.crt. Next: sudo nginx -t && sudo systemctl reload nginx"
