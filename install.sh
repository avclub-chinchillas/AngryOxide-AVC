#!/bin/bash
#
# AngryOxide-AVClub end-to-end installer.
#
#   * installs system (apt) dependencies, including the build toolchain
#   * installs a Rust toolchain if one is missing or too old
#   * builds the angryoxide binary from source and installs it
#   * installs bash/zsh completions
#   * creates the avc-venv virtual environment as root and installs the
#     Python dependencies into it
#
# Every step is idempotent: re-running only does the work that is still
# missing, and reports what it skipped.
#
# Usage: sudo ./install.sh [install|uninstall|help]

set -uo pipefail

prog="angryoxide"

# Overridable so the installer can be pointed at a staging prefix.
: "${BIN_DIR:=/usr/bin}"
: "${VENV_DIR:=avc-venv}"
: "${BASH_COMPLETION_DIR:=/etc/bash_completion.d}"
: "${ZSH_COMPLETION_DIR:=/home}"

bash_completion_script="completions/bash_angryoxide_completions"
zsh_completion_script="completions/zsh_angryoxide_completions"

RUSTUP_HOME_SYSTEM="/usr/local/rustup"
CARGO_HOME_SYSTEM="/usr/local/cargo"
MIN_RUST_VERSION="1.70"  # see rust-version in Cargo.toml

APT_RUNTIME=(python3 python3-venv python3-pip sshpass wireless-tools iw curl whiptail)
APT_BUILD=(build-essential pkg-config libssl-dev git)
APT_OPTIONAL=(hashcat wordlists)

export DEBIAN_FRONTEND=noninteractive

CARGO_BIN=""       # cargo to build with
CARGO_RUN_AS=""    # non-empty when cargo must run as that user, not root
APT_UPDATED=""

# Always operate on the project directory, whatever the caller's cwd is.
cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" || exit 1

# ======================
# Output helpers
# ======================

info() { echo "[*] $*"; }
ok()   { echo "[+] $*"; }
skip() { echo "[=] $*"; }
warn() { echo "[!] $*" >&2; }
fail() { echo "[!] $*" >&2; exit 1; }

section() {
    echo ""
    echo "=========================================="
    echo "  $*"
    echo "=========================================="
}

check_root() {
    if [[ "$(id -u)" -ne 0 ]]; then
        echo "This operation must be run as root. Please use sudo." >&2
        exit 1
    fi
}

user_home() {
    [[ -n "${SUDO_USER:-}" ]] || return 1
    getent passwd "$SUDO_USER" | cut -d: -f6
}

# Is $1 >= $2, comparing dotted version numbers?
version_at_least() {
    [[ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" == "$2" ]]
}

# ======================
# System dependencies
# ======================

require_apt() {
    command -v apt-get &> /dev/null || \
        fail "This installer needs apt-get (Debian/Ubuntu). Install the dependencies manually on other distros."
}

package_installed() {
    dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "^install ok installed$"
}

apt_update_once() {
    if [[ -z "$APT_UPDATED" ]]; then
        info "Updating package lists..."
        apt-get update -qq
        APT_UPDATED=1
    fi
}

# install_packages <label> <package>...
install_packages() {
    local label="$1"; shift
    local missing=() pkg

    for pkg in "$@"; do
        if package_installed "$pkg"; then
            skip "$pkg already installed"
        else
            missing+=("$pkg")
        fi
    done

    if [[ ${#missing[@]} -eq 0 ]]; then
        return 0
    fi

    apt_update_once
    info "Installing $label: ${missing[*]}"
    apt-get install -y "${missing[@]}" || return 1

    for pkg in "${missing[@]}"; do
        package_installed "$pkg" || { warn "$pkg failed to install."; return 1; }
    done
    ok "Installed $label."
}

# Optional packages never block the install.
install_optional_packages() {
    local pkg
    for pkg in "$@"; do
        if package_installed "$pkg"; then
            skip "$pkg already installed"
            continue
        fi
        apt_update_once
        info "Installing optional: $pkg"
        if apt-get install -y "$pkg" &> /dev/null && package_installed "$pkg"; then
            ok "$pkg installed."
        else
            warn "Optional package $pkg is unavailable (cracking features may need it)."
        fi
    done
}

install_system_dependencies() {
    check_root
    require_apt
    install_packages "runtime dependencies" "${APT_RUNTIME[@]}" || fail "Failed to install runtime dependencies."
    install_packages "build dependencies" "${APT_BUILD[@]}" || fail "Failed to install build dependencies."
    install_optional_packages "${APT_OPTIONAL[@]}"
}

# ======================
# Rust toolchain
# ======================

# Locate a usable cargo, preferring system-wide installs that work as root.
detect_cargo() {
    CARGO_BIN=""
    CARGO_RUN_AS=""
    local candidate home

    for candidate in "$(command -v cargo 2>/dev/null)" "$CARGO_HOME_SYSTEM/bin/cargo" "/usr/bin/cargo"; do
        if [[ -n "$candidate" && -x "$candidate" ]]; then
            CARGO_BIN="$candidate"
            return 0
        fi
    done

    # A rustup toolchain owned by the invoking user has to run as that user,
    # otherwise the shim looks for toolchains under root's RUSTUP_HOME.
    if home="$(user_home)" && [[ -n "$home" && -x "$home/.cargo/bin/cargo" ]]; then
        CARGO_BIN="$home/.cargo/bin/cargo"
        CARGO_RUN_AS="$SUDO_USER"
        return 0
    fi

    return 1
}

run_cargo() {
    if [[ -n "$CARGO_RUN_AS" ]]; then
        sudo -H -u "$CARGO_RUN_AS" "$CARGO_BIN" "$@"
    elif [[ -d "$RUSTUP_HOME_SYSTEM" ]]; then
        RUSTUP_HOME="$RUSTUP_HOME_SYSTEM" "$CARGO_BIN" "$@"
    else
        "$CARGO_BIN" "$@"
    fi
}

cargo_version() {
    run_cargo --version 2>/dev/null | awk '{print $2}'
}

install_rustup() {
    command -v curl &> /dev/null || { warn "curl is required to install Rust via rustup."; return 1; }

    info "Installing Rust via rustup into $RUSTUP_HOME_SYSTEM (system-wide)..."
    # SKIP_PATH_CHECK: an apt-installed rustc/cargo is expected here and must
    # not abort the install - the rustup toolchain takes precedence via
    # /usr/local/bin.
    RUSTUP_HOME="$RUSTUP_HOME_SYSTEM" CARGO_HOME="$CARGO_HOME_SYSTEM" RUSTUP_INIT_SKIP_PATH_CHECK=yes \
        bash -c "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --profile minimal" \
        || { warn "rustup installation failed."; return 1; }

    # Readable by everyone so non-root users can build too.
    chmod -R a+rX "$RUSTUP_HOME_SYSTEM" "$CARGO_HOME_SYSTEM" 2>/dev/null

    local tool
    for tool in cargo rustc rustup; do
        [[ -x "$CARGO_HOME_SYSTEM/bin/$tool" ]] && ln -sf "$CARGO_HOME_SYSTEM/bin/$tool" "/usr/local/bin/$tool"
    done

    # The shims need RUSTUP_HOME; CARGO_HOME stays per-user so that each
    # user keeps their own crate cache in ~/.cargo.
    printf '# Added by AngryOxide-AVClub install.sh\nexport RUSTUP_HOME=%s\n' "$RUSTUP_HOME_SYSTEM" \
        > /etc/profile.d/rust-avc.sh
    chmod 0644 /etc/profile.d/rust-avc.sh

    CARGO_BIN="$CARGO_HOME_SYSTEM/bin/cargo"
    CARGO_RUN_AS=""
    [[ -x "$CARGO_BIN" ]] || { warn "rustup finished but $CARGO_BIN is missing."; return 1; }
    ok "Rust installed: $(cargo_version)"
}

ensure_rust_toolchain() {
    check_root
    local version

    if detect_cargo; then
        version="$(cargo_version)"
        if [[ -n "$version" ]] && version_at_least "$version" "$MIN_RUST_VERSION"; then
            skip "Rust toolchain present: cargo $version ($CARGO_BIN)"
            return 0
        fi
        if [[ -n "$version" ]]; then
            warn "cargo $version is older than the required $MIN_RUST_VERSION."
        else
            warn "Found $CARGO_BIN but it does not run; installing a working toolchain."
        fi
    else
        info "No Rust toolchain found."
    fi

    # Distro packages first - no piping a script from the network.
    if ! package_installed cargo; then
        apt_update_once
        info "Installing Rust from apt (rustc, cargo)..."
        apt-get install -y rustc cargo &> /dev/null
    fi

    if detect_cargo; then
        version="$(cargo_version)"
        if [[ -n "$version" ]] && version_at_least "$version" "$MIN_RUST_VERSION"; then
            ok "Rust toolchain installed: cargo $version ($CARGO_BIN)"
            return 0
        fi
        warn "apt provides cargo ${version:-unknown}, older than the required $MIN_RUST_VERSION."
    fi

    install_rustup
}

# ======================
# Build and install
# ======================

build_binaries() {
    [[ -n "$CARGO_BIN" ]] || { warn "No cargo available to build with."; return 1; }

    info "Building $prog in release mode (first build takes several minutes)..."
    run_cargo build --release || { warn "cargo build failed."; return 1; }

    [[ -f "target/release/$prog" ]] || { warn "Build finished but target/release/$prog is missing."; return 1; }
    ok "Build complete: target/release/$prog"

    # Building as root leaves target/ root-owned; hand it back so the user can
    # run cargo themselves afterwards.
    if [[ -z "$CARGO_RUN_AS" && -n "${SUDO_USER:-}" ]]; then
        chown -R "$SUDO_USER:" target 2>/dev/null
    fi
}

find_binary() {
    local candidate
    for candidate in "target/release/$prog" "./$prog" "target/debug/$prog"; do
        if [[ -f "$candidate" ]]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

install_binary() {
    check_root
    local binary
    binary="$(find_binary)" || fail "No $prog binary found to install. Build it with: cargo build --release"

    if [[ -x "$BIN_DIR/$prog" ]] && cmp -s "$binary" "$BIN_DIR/$prog"; then
        skip "$BIN_DIR/$prog is already up to date."
        return 0
    fi

    mkdir -p "$BIN_DIR"
    # Remove first: overwriting a running binary fails with "Text file busy".
    rm -f "$BIN_DIR/$prog"
    install -m 0755 "$binary" "$BIN_DIR/$prog" || fail "Failed to install $binary to $BIN_DIR/$prog."
    [[ -x "$BIN_DIR/$prog" ]] || fail "$prog is missing from $BIN_DIR after install."
    ok "Installed $binary -> $BIN_DIR/$prog"
}

install_bash() {
    check_root
    if ! command -v bash &> /dev/null; then
        skip "Bash not found, skipping bash completion."
        return 0
    fi
    mkdir -p "$BASH_COMPLETION_DIR"
    if cmp -s "$bash_completion_script" "$BASH_COMPLETION_DIR/$prog"; then
        skip "Bash completion already installed."
        return 0
    fi
    cp "$bash_completion_script" "$BASH_COMPLETION_DIR/$prog" || { warn "Failed to install bash completion."; return 0; }
    ok "Bash completion installed."
}

install_zsh() {
    check_root
    if ! command -v zsh &> /dev/null; then
        skip "Zsh not found, skipping zsh completion."
        return 0
    fi

    local installed=0 dir user zsh_dir
    for dir in "$ZSH_COMPLETION_DIR"/*/; do
        [[ -d "$dir" ]] || continue
        [[ "$dir" =~ ^/home/\. ]] && continue
        user="$(basename "$dir")"
        id "$user" &> /dev/null || continue

        zsh_dir="${dir%/}/.zsh/completion"
        if cmp -s "$zsh_completion_script" "$zsh_dir/_$prog"; then
            skip "Zsh completion already installed for $user"
            continue
        fi
        mkdir -p "$zsh_dir"
        cp "$zsh_completion_script" "$zsh_dir/_$prog" || continue
        chown "$user:" "$zsh_dir/_$prog" 2>/dev/null
        ok "Zsh completion installed for $user"
        ((installed++))
    done
    [[ $installed -eq 0 ]] && skip "No zsh completions needed updating."
    return 0
}

# ======================
# Python environment
# ======================

setup_venv() {
    check_root

    if [[ -x "$VENV_DIR/bin/python3" ]]; then
        skip "Virtual environment '$VENV_DIR' already present."
        return 0
    fi

    if [[ -d "$VENV_DIR" ]]; then
        # Only clear it out if it really is a broken venv, never an unrelated dir.
        if [[ -f "$VENV_DIR/pyvenv.cfg" || -z "$(ls -A "$VENV_DIR" 2>/dev/null)" ]]; then
            warn "'$VENV_DIR' exists but is incomplete; recreating it."
            rm -rf "${VENV_DIR:?}"
        else
            fail "'$VENV_DIR' exists and is not a virtual environment. Move it aside and re-run."
        fi
    fi

    info "Creating virtual environment '$VENV_DIR' as root..."
    python3 -m venv "$VENV_DIR" || fail "Failed to create virtual environment."
    [[ -x "$VENV_DIR/bin/python3" ]] || fail "Virtual environment was created without a python3."
    ok "Virtual environment created at $(readlink -f "$VENV_DIR")"
}

install_python_deps() {
    check_root
    [[ -x "$VENV_DIR/bin/python3" ]] || fail "Virtual environment '$VENV_DIR' is missing. Run setup first."
    [[ -f requirements.txt ]] || fail "requirements.txt not found."

    info "Upgrading pip tooling in $VENV_DIR..."
    "$VENV_DIR/bin/python3" -m pip install --upgrade pip setuptools wheel -q \
        || warn "Could not upgrade pip/setuptools/wheel; continuing with what is installed."

    # pip is idempotent: satisfied requirements are left alone.
    info "Installing Python dependencies from requirements.txt..."
    "$VENV_DIR/bin/python3" -m pip install -r requirements.txt -q \
        || fail "Failed to install Python dependencies."
    ok "Python dependencies installed into $VENV_DIR."
}

# ======================
# Verification
# ======================

verify_install() {
    local failures=0 version

    if [[ -x "$BIN_DIR/$prog" ]]; then
        version="$(timeout 10 "$BIN_DIR/$prog" --version 2>/dev/null | head -n1)"
        ok "$prog installed at $BIN_DIR/$prog${version:+ ($version)}"
    else
        warn "$prog is NOT installed at $BIN_DIR/$prog"
        ((failures++))
    fi

    if [[ -x "$VENV_DIR/bin/python3" ]] && "$VENV_DIR/bin/python3" -c 'import pandas, kafka' &> /dev/null; then
        ok "Python environment OK (pandas, kafka importable)"
    else
        warn "Python dependencies are NOT importable from $VENV_DIR"
        ((failures++))
    fi

    return "$failures"
}

print_summary() {
    local status="$1"

    section "Installation complete"
    if [[ "$status" -ne 0 ]]; then
        warn "Finished with $status problem(s) - see the messages above."
    fi
    echo "[*] To pick a tool from the TUI launcher:"
    echo "    sudo ./avc-launcher.sh"
    echo ""
    echo "[*] To run the program directly:"
    echo "    source $VENV_DIR/bin/activate"
    echo "    python3 AVC.py [OPTIONS]"
    echo ""
    echo "[*] To run the cracking checker:"
    echo "    source $VENV_DIR/bin/activate"
    echo "    python3 AVC-CC.py -o results.txt [OPTIONS]"
    echo ""
    echo "[*] To uninstall:  sudo ./uninstall.sh"
    echo "=========================================="
}

# ======================
# Entry points
# ======================

do_install() {
    check_root
    require_apt

    section "1/5  System dependencies"
    install_system_dependencies

    section "2/5  Rust toolchain"
    if ensure_rust_toolchain; then
        section "3/5  Building $prog"
        build_binaries || fail "Build failed. Fix the errors above and re-run."
    else
        warn "Could not install a Rust toolchain."
        section "3/5  Building $prog"
        if find_binary > /dev/null; then
            warn "Using the existing prebuilt binary: $(find_binary)"
        else
            fail "No Rust toolchain and no prebuilt $prog binary - cannot continue."
        fi
    fi

    section "4/5  Installing binary and completions"
    install_binary
    install_bash
    install_zsh

    section "5/5  Python environment"
    setup_venv
    install_python_deps

    section "Verifying"
    verify_install
    print_summary "$?"
}

uninstall() {
    check_root
    echo "Uninstalling $prog..."
    rm -f "$BIN_DIR/$prog"
    rm -f "$BASH_COMPLETION_DIR/$prog"
    for dir in "$ZSH_COMPLETION_DIR"/*; do
        if [[ -d "$dir" ]]; then
            rm -f "$dir/.zsh/completion/_$prog"
        fi
    done
    echo "Cleaned installed binary and completion scripts."
    echo "[*] For a full cleanup (venv, caches, hashes), run: sudo ./uninstall.sh"
}

usage() {
    cat <<EOF
AngryOxide-AVClub installer

Usage: sudo ./install.sh [command]

Commands:
  install      Full end-to-end install (default)
  uninstall    Remove the binary and shell completions
  help         Show this message

The install is idempotent - re-run it any time to repair or update.
Steps: apt dependencies -> Rust toolchain -> cargo build --release ->
binary + completions -> root-owned $VENV_DIR with requirements.txt.
EOF
}

case "${1:-install}" in
    install)
        do_install
        ;;
    uninstall)
        uninstall
        ;;
    help|-h|--help)
        usage
        ;;
    *)
        warn "Unknown command: $1"
        usage
        exit 1
        ;;
esac
