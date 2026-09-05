#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
STEP="${1:-1}"

case "$STEP" in
  1)
    echo "=== [Step 1] Issuer Schema & Credential Definition ==="
    docker run --rm --network von_von \
      -v "$SCRIPT_DIR":/workspace \
      -v "$SCRIPT_DIR/.indy_client":/home/indy/.indy_client \
      -w /workspace \
      von-network-base python3 /workspace/1_issuer_schema_cred_def.py
    ;;
  2)
    echo "=== [Step 2] Request & Issue Credential (VC 발급) ==="
    docker run --rm --network von_von \
      -v "$SCRIPT_DIR":/workspace \
      -v "$SCRIPT_DIR/.indy_client":/home/indy/.indy_client \
      -w /workspace \
      von-network-base python3 /workspace/2_issue_credential.py
    ;;
  3)
    echo "=== [Step 3] Verify Presentation (VP 검증) ==="
    docker run --rm --network von_von \
      -v "$SCRIPT_DIR":/workspace \
      -v "$SCRIPT_DIR/.indy_client":/home/indy/.indy_client \
      -w /workspace \
      von-network-base python3 /workspace/3_verify_presentation.py
    ;;
  *)
    echo "사용법: ./run.sh [1|2|3]"
    exit 1
    ;;
esac
