#!/bin/bash

# List interfaces
iwconfig
# Run the command and capture the output into an array
readarray -t result_array <<< "$(iwconfig | awk -F'[ :=]+' 'BEGIN {OFS=","} {if ($1 != "" && $1 != "off") print $1}')"

# Display the available options
for index in "${!result_array[@]}"; do
    echo "[$index] ${result_array[index]}"
done

# Prompt the user to select an option
read -p "Select the attack interface: " selected_index

# Store the selected option in a variable
MON_INTERFACE=${result_array[selected_index]}

# Display the selected option
echo "Selected interface: $MON_INTERFACE"

sudo angryoxide -i $MON_INTERFACE -c 1,2,3,4,5,6,7,8,10,11,12,13 -w whitelist.txt -r 3 --headless --notar

