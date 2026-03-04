#!/usr/bin/env bash
# Sets up a uv-only environment on local disk.
# Patches the venv activate script to export UV_PROJECT_ENVIRONMENT,
# and creates a convenience activate.sh in the project root.
#
# Usage: ./scripts/setup_uv_env.sh

set -euo pipefail

ENV_NAME="{{ cookiecutter.package_name }}"
ENV_PATH="${HOME}/.local/share/uv/envs/${ENV_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Set UV_PROJECT_ENVIRONMENT and create the venv
export UV_PROJECT_ENVIRONMENT="${ENV_PATH}"
echo "Creating uv environment at: ${ENV_PATH}"
uv sync

# Patch the venv activate script to set UV_PROJECT_ENVIRONMENT on activate
ACTIVATE_SCRIPT="${ENV_PATH}/bin/activate"
if ! grep -q "UV_PROJECT_ENVIRONMENT" "${ACTIVATE_SCRIPT}" 2>/dev/null; then
    cat >> "${ACTIVATE_SCRIPT}" << EOF

# Added by setup_uv_env.sh — keeps uv commands pointing to this environment
export UV_PROJECT_ENVIRONMENT="${ENV_PATH}"
EOF
    echo "Patched ${ACTIVATE_SCRIPT} with UV_PROJECT_ENVIRONMENT"
fi

# Create convenience activate script in project root
cat > "${PROJECT_DIR}/activate.sh" << EOF
#!/usr/bin/env bash
# Activate the uv environment for ${ENV_NAME}.
# Usage: source activate.sh
source "${ENV_PATH}/bin/activate"
EOF

echo ""
echo "Done! To activate:"
echo "  source activate.sh"
