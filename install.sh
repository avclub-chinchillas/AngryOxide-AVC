#!/bin/bash

prog="angryoxide"
bash_completion_script="completions/bash_angryoxide_completions"
zsh_completion_script="completions/zsh_angryoxide_completions"
BASH_COMPLETION_DIR="/etc/bash_completion.d"
ZSH_COMPLETION_DIR="/home"

check_root() {
    if [[ "$(id -u)" -ne 0 ]]; then
        echo "This operation must be run as root. Please use sudo." >&2
        exit 1
    fi
}

install_apt_dependencies() {
    check_root
    echo "Installing system dependencies via apt..."

    # Define required packages
    local required_packages=(
        "python3"
        "python3-venv"
        "python3-pip"
        "sshpass"
        "wireless-tools"
        "iw"
        "curl"
    )

    # Define optional packages (for cracking features)
    local optional_packages=(
        "hashcat"
        "wordlists"
    )

    # Update package list
    echo "[*] Updating package list..."
    apt-get update -qq

    # Install each required package
    for package in "${required_packages[@]}"; do
        if dpkg -l | grep -q "^ii  $package"; then
            echo "[+] $package is already installed."
        else
            echo "[*] Installing $package..."
            apt-get install -y "$package"
            if [[ $? -eq 0 ]]; then
                echo "[+] $package installed successfully."
            else
                echo "[!] Failed to install $package." >&2
                exit 1
            fi
        fi
    done

    # Install optional packages (continue if they fail)
    echo "[*] Installing optional packages for cracking features..."
    for package in "${optional_packages[@]}"; do
        if dpkg -l | grep -q "^ii  $package"; then
            echo "[+] $package is already installed."
        else
            echo "[*] Installing optional: $package..."
            apt-get install -y "$package" 2>/dev/null
            if [[ $? -eq 0 ]]; then
                echo "[+] $package installed successfully."
            else
                echo "[!] Optional package $package not available (this is OK)."
            fi
        fi
    done

    echo "[+] System dependencies installation completed."
}

setup_venv() {
    echo "Setting up Python virtual environment..."
    if [[ -d "avc-venv" ]]; then
        echo "Virtual environment 'avc-venv' already exists, skipping creation."
    else
        echo "Creating virtual environment 'avc-venv'..."
        python3 -m venv avc-venv
        if [[ $? -ne 0 ]]; then
            echo "Failed to create virtual environment." >&2
            exit 1
        fi
        echo "Virtual environment created successfully."
    fi
}

install_binary() {
    check_root
    echo "Installing $prog binary..."
    chmod +x $prog
    cp "$prog" "/usr/bin/$prog"
}

install_python_deps() {
    echo "Installing Python dependencies into virtual environment..."
    if [[ ! -d "avc-venv" ]]; then
        echo "Virtual environment not found. Creating it now..."
        setup_venv
    fi
    source avc-venv/bin/activate

    # Check if dependencies are already installed
    echo "[*] Checking for already-installed Python packages..."
    if pip freeze | grep -q "pandas" && pip freeze | grep -q "kafka"; then
        echo "[+] Python dependencies are already installed."
    else
        echo "[*] Installing Python dependencies..."
        pip install --upgrade pip setuptools wheel -q
        pip install -r requirements.txt -q
        if [[ $? -eq 0 ]]; then
            echo "[+] Python dependencies installed successfully in avc-venv."
        else
            echo "[!] Failed to install Python dependencies." >&2
            deactivate
            exit 1
        fi
    fi

    deactivate
}

install_bash() {
    check_root
    if command -v bash &> /dev/null; then
        echo "Installing bash completion for $prog..."
        mkdir -p "$BASH_COMPLETION_DIR"
        cp "$bash_completion_script" "$BASH_COMPLETION_DIR/$prog"
        echo "Bash completion installed successfully."
    else
        echo "Bash not found, skipping Bash completion installation."
    fi
}

install_zsh() {
    check_root
    if command -v zsh &> /dev/null; then
        echo "Installing zsh completion for $prog for all users..."
        for dir in $ZSH_COMPLETION_DIR/*/; do
            if [[ -d "$dir" && ! "$dir" =~ ^/home/\. ]]; then
                user=$(basename "$dir")
                # Skip system users and invalid directories
                if id "$user" &>/dev/null 2>&1; then
                    zsh_dir="$dir/.zsh/completion"
                    echo "Installing for user $user..."
                    mkdir -p "$zsh_dir"
                    cp "$zsh_completion_script" "$zsh_dir/_$prog"
                    chown "$user:$user" "$zsh_dir/_$prog"
                fi
            fi
        done
        echo "Zsh completion installed successfully for all users."
    else
        echo "Zsh not found, skipping Zsh completion installation."
    fi
}

uninstall() {
    check_root
    echo "Uninstalling $prog..."
    rm -f "/usr/bin/$prog"
    rm -f "$BASH_COMPLETION_DIR/$prog"
    for dir in $ZSH_COMPLETION_DIR/*; do
        if [[ -d "$dir" ]]; then
            rm -f "$dir/.zsh/completion/_$prog"
        fi
    done
    echo "Cleaned installed binary and completion scripts."
}

case "$1" in
    install)
        install_apt_dependencies
        setup_venv
        install_binary
        install_bash
        install_zsh
        install_python_deps
        echo ""
        echo "=========================================="
        echo "[+] Installation completed successfully!"
        echo "=========================================="
        echo "[*] To run the program:"
        echo "    source avc-venv/bin/activate"
        echo "    python3 AVC.py [OPTIONS]"
        echo ""
        echo "[*] To run the cracking checker:"
        echo "    source avc-venv/bin/activate"
        echo "    python3 AVC-CC.py -o results.txt [OPTIONS]"
        echo "=========================================="
        ;;
    uninstall)
        uninstall
        ;;
    *)
        install_apt_dependencies
        setup_venv
        install_binary
        install_bash
        install_zsh
        install_python_deps
        echo ""
        echo "=========================================="
        echo "[+] Installation completed successfully!"
        echo "=========================================="
        echo "[*] To run the program:"
        echo "    source avc-venv/bin/activate"
        echo "    python3 AVC.py [OPTIONS]"
        echo ""
        echo "[*] To run the cracking checker:"
        echo "    source avc-venv/bin/activate"
        echo "    python3 AVC-CC.py -o results.txt [OPTIONS]"
        echo "=========================================="
        ;;
esac
