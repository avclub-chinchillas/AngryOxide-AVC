#!/bin/bash

declare -a hash_files=()

for file in *.hc22000; do
    if [[ -f "$file" && ! " ${hash_files[@]} " =~ " $file " ]]; then
        hash_files+=("$file")
    fi
done

#echo "[*] Unique hash files found: ${hash_files[@]}"
#echo "[*] Count of unique hash files: ${#hash_files[@]}"