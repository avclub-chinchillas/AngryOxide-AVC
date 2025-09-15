#!/bin/bash

# List interfaces
iwconfig
# Run the command and capture the output into an array
readarray -t result_array <<< "$(iwconfig | awk -F'[ :=]+' 'BEGIN {OFS=","} {if ($1 != "" && $1 != "off") print $1}')"

# Select the third interface (index 2)
MON_INTERFACE=${result_array[2]}

# Display the selected option
echo "Selected interface: $MON_INTERFACE"

sudo angryoxide -i $MON_INTERFACE -c 1,2,3,4,5,6,7,8,10,11,12,13 -w whitelist.txt -r 3 --headless --notar

