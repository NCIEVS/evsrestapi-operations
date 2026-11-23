#!/bin/sh
# Usage: verify-sha512.sh FILE CHECKSUM-FILE
# Fails unless FILE matches the SHA-512 in CHECKSUM-FILE. Accepts the layouts Apache uses:
# "HASH  name", a bare HASH, or gpg's "name: HA SH ..." form (spaced, upper case, wrapped).
set -e
file=$1
sums=$(cat "$2")
case "$sums" in
  *:*) expected=$(printf '%s' "${sums#*:}" | tr -d ' \t\r\n') ;;
  *) expected=$(printf '%s\n' "$sums" | head -n 1 | awk '{print $1}') ;;
esac
expected=$(printf '%s' "$expected" | tr 'A-F' 'a-f')
actual=$(sha512sum "$file" | awk '{print $1}')
if [ "${#expected}" -ne 128 ] || [ "$expected" != "$actual" ]; then
  echo "ERROR: SHA-512 check failed for $file" >&2
  exit 1
fi
echo "SHA-512 verified: $file"
