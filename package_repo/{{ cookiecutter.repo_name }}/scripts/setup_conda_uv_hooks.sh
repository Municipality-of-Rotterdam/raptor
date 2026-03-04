#!/usr/bin/env bash
# Sets up conda activate/deactivate hooks so that UV_PROJECT_ENVIRONMENT
# is automatically configured when activating the conda environment.
# This is an alternative to using direnv.
#
# Usage: ./scripts/setup_conda_uv_hooks.sh

set -euo pipefail

ENV_NAME="{{ cookiecutter.package_name }}"
CONDA_PREFIX="${CONDA_PREFIX:-$(conda info --base)/envs/${ENV_NAME}}"

# Resolve the conda env path
if conda env list | grep -q "^${ENV_NAME} "; then
    ENV_PATH=$(conda env list | grep "^${ENV_NAME} " | awk '{print $NF}')
elif [ -d "${CONDA_PREFIX}" ]; then
    ENV_PATH="${CONDA_PREFIX}"
else
    echo "Error: conda environment '${ENV_NAME}' not found."
    echo "Create it first: conda env create --file environment.yml"
    exit 1
fi

ACTIVATE_DIR="${ENV_PATH}/etc/conda/activate.d"
DEACTIVATE_DIR="${ENV_PATH}/etc/conda/deactivate.d"

mkdir -p "${ACTIVATE_DIR}" "${DEACTIVATE_DIR}"

# Create activate hook
cat > "${ACTIVATE_DIR}/uv_project_env.sh" << EOF
#!/usr/bin/env bash
export UV_PROJECT_ENVIRONMENT="${ENV_PATH}"
EOF

# Create deactivate hook
cat > "${DEACTIVATE_DIR}/uv_project_env.sh" << 'EOF'
#!/usr/bin/env bash
unset UV_PROJECT_ENVIRONMENT
EOF

echo "Conda hooks installed for '${ENV_NAME}':"
echo "  activate:   ${ACTIVATE_DIR}/uv_project_env.sh"
echo "  deactivate: ${DEACTIVATE_DIR}/uv_project_env.sh"
echo ""
echo "UV_PROJECT_ENVIRONMENT will be set to '${ENV_PATH}' on 'conda activate ${ENV_NAME}'."
