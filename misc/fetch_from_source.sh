#!/usr/bin/env bash
set -euo pipefail

# Default values
: "${MODE:=GIT_HTML}"
: "${OUT_DIR:=/data}"
: "${STATE_DIR:=/data/.state}"

mkdir -p "${OUT_DIR}" "${STATE_DIR}"

# Fetch links based on the selected mode
if [[ "${MODE}" == "GIT_HTML" ]]; then
  : "${LINKS_GIT_NAMESPACE:?}"
  : "${LINKS_GIT_NAME:?}"
  : "${GITHUB_ORG:?}"
  : "${GITHUB_REPO:?}"
  : "${FILE_PATH:?}"

  # Get the latest revision from the Flux GitRepository status
  REVISION="$(kubectl -n "${LINKS_GIT_NAMESPACE}" get gitrepository.source.toolkit.fluxcd.io "${LINKS_GIT_NAME}" -o jsonpath='{.status.artifact.revision}')"
  if [[ -z "${REVISION}" ]]; then
    echo "Flux GitRepository has no revision yet; exiting."
    exit 0
  fi

  # Extract SHA from revision
  SHA="${REVISION##*/}"

  # Check if this SHA has already been processed
  LAST_FILE="${STATE_DIR}/last_sha.txt"

  # Read last processed SHA
  LAST=""; [[ -f "${LAST_FILE}" ]] && LAST="$(cat "${LAST_FILE}")"

  # If SHA matches last processed, exit
  if [[ "${SHA}" == "${LAST}" ]]; then
    echo "No new commit for index.html source (sha=${SHA})."
    exit 0
  fi

  # Download the raw HTML file from GitHub
  RAW_URL="https://raw.githubusercontent.com/${GITHUB_ORG}/${GITHUB_REPO}/${SHA}/${FILE_PATH}"
  echo "Downloading ${RAW_URL}"
  HDR=()
  [[ -n "${GITHUB_TOKEN:-}" ]] && HDR=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
  curl -fsSL "${HDR[@]}" -o "${OUT_DIR}/index.html" "${RAW_URL}"

  # Process the HTML to extract links
  python /app/scrape_links.py "${OUT_DIR}/index.html" "${OUT_DIR}/links.yaml"
  rm -f "${OUT_DIR}/index.html"
  echo -n "${SHA}" > "${LAST_FILE}"
  echo "Processed sha=${SHA}"