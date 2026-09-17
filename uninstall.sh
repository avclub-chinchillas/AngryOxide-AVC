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

uninstall_binary() {
    check_root
    echo "[*] Removing $prog binary..."
    rm -f "/usr/bin/$prog"
    if [[ $? -eq 0 ]]; then
        echo "[+] Binary removed."
    else
        echo "[!] Failed to remove binary."
    fi
}

uninstall_bash_completion() {
    check_root
    echo "[*] Removing bash completion..."
    rm -f "$BASH_COMPLETION_DIR/$prog"
    if [[ $? -eq 0 ]]; then
        echo "[+] Bash completion removed."
    else
        echo "[!] Failed to remove bash completion."
    fi
}

uninstall_zsh_completion() {
    check_root
    echo "[*] Removing zsh completion for all users..."
    removed_count=0
    for dir in $ZSH_COMPLETION_DIR/*/; do
        if [[ -d "$dir" && ! "$dir" =~ ^/home/\. ]]; then
            user=$(basename "$dir")
            if id "$user" &>/dev/null 2>&1; then
                zsh_completion_file="$dir/.zsh/completion/_$prog"
                if [[ -f "$zsh_completion_file" ]]; then
                    rm -f "$zsh_completion_file"
                    if [[ $? -eq 0 ]]; then
                        echo "[+] Zsh completion removed for $user"
                        ((removed_count++))
                    fi
                fi
            fi
        fi
    done
    if [[ $removed_count -eq 0 ]]; then
        echo "[*] No zsh completions found to remove."
    fi
}

remove_venv() {
    echo "[*] Removing virtual environment 'avc-venv'..."
    if [[ -d "avc-venv" ]]; then
        rm -rf avc-venv
        if [[ $? -eq 0 ]]; then
            echo "[+] Virtual environment removed."
        else
            echo "[!] Failed to remove virtual environment."
        fi
    else
        echo "[*] Virtual environment not found."
    fi
}

remove_pycache() {
    echo "[*] Removing Python cache files..."
    found_cache=0
    while IFS= read -r -d '' pycache_dir; do
        echo "[+] Removing $pycache_dir"
        rm -rf "$pycache_dir"
        ((found_cache++))
    done < <(find . -type d -name "__pycache__" -print0)

    if [[ $found_cache -eq 0 ]]; then
        echo "[*] No __pycache__ directories found."
    else
        echo "[+] Removed $found_cache __pycache__ directories."
    fi
}

remove_pyc_files() {
    echo "[*] Removing compiled Python files (.pyc, .pyo)..."
    found_pyc=0
    while IFS= read -r -d '' pyc_file; do
        rm -f "$pyc_file"
        ((found_pyc++))
    done < <(find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -print0)

    if [[ $found_pyc -eq 0 ]]; then
        echo "[*] No compiled Python files found."
    else
        echo "[+] Removed $found_pyc compiled Python files."
    fi
}

remove_hashes_folder() {
    echo "[*] Removing 'hashes' folder..."
    if [[ -d "hashes" ]]; then
        rm -rf hashes
        if [[ $? -eq 0 ]]; then
            echo "[+] Hashes folder removed."
        else
            echo "[!] Failed to remove hashes folder."
        fi
    else
        echo "[*] Hashes folder not found."
    fi
}

remove_egg_info() {
    echo "[*] Removing .egg-info directories..."
    found_egg=0
    while IFS= read -r -d '' egg_dir; do
        echo "[+] Removing $egg_dir"
        rm -rf "$egg_dir"
        ((found_egg++))
    done < <(find . -type d -name "*.egg-info" -print0)

    if [[ $found_egg -eq 0 ]]; then
        echo "[*] No .egg-info directories found."
    else
        echo "[+] Removed $found_egg .egg-info directories."
    fi
}

show_summary() {
    echo ""
    echo "=========================================="
    echo "[*] Uninstallation Summary:"
    echo "=========================================="
    echo "[+] Removed angryoxide binary from /usr/bin/"
    echo "[+] Removed bash and zsh completions"
    echo "[+] Removed Python virtual environment (avc-venv)"
    echo "[+] Removed Python cache and compiled files"
    echo "[+] Removed hashes folder"
    echo ""
    echo "[*] AngryOxide-AVClub has been uninstalled."
    echo "[!] Note: Config files and README remain. To remove all files, run: rm -rf ."
    echo "=========================================="
}

main() {
    echo "=========================================="
    echo "[!] AngryOxide-AVClub Uninstaller"
    echo "=========================================="
    echo ""
    echo "[!] This will remove:"
    echo "  - angryoxide binary from /usr/bin/"
    echo "  - bash and zsh shell completions"
    echo "  - Python virtual environment (avc-venv)"
    echo "  - Python cache and compiled files"
    echo "  - hashes folder and captured hash files"
    echo ""
    read -p "[?] Continue with uninstallation? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "[*] Uninstallation cancelled."
        exit 0
    fi

    echo ""
    uninstall_binary
    uninstall_bash_completion
    uninstall_zsh_completion
    remove_venv
    remove_pycache
    remove_pyc_files
    remove_hashes_folder
    remove_egg_info
    show_summary
}

main
