#!/bin/bash
# Oracle for image_to_cad tasks. These cases have no authored build script —
# the ground-truth is the parametric reference.FCStd itself — so the oracle
# copies that reference to the declared answer path, which exercises the scorer
# alone and should score 1.0 (the reference is a valid single PartDesign Body,
# so it passes the structural gate). A stub answer.py satisfies the artifact
# contract the verifier checks.
set -euo pipefail

cp /solution/reference.FCStd /app/answer.FCStd
printf '# oracle: answer produced by copying the held-back reference FCStd\n' > /app/answer.py

test -f /app/answer.py
test -f /app/answer.FCStd
