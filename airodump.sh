#!/bin/bash

#WRITE_INTERVAL=10
#SLEEP_INTERVAL=$WRITE_INTERVAL+2

# List interfaces
iwconfig
# Run the command and capture the output into an array
#readarray -t result_array <<< "$(iwconfig | awk -F'[ :=]+' 'BEGIN {OFS=","} {if ($1 != "" && $1 != "off") print $1}')"

# Select the third interface (index 2)
#MON_INTERFACE=${result_array[2]}
MON_INTERFACE="wlan1mon"

# Display the selected option
#echo "Selected interface: $MON_INTERFACE"

# Start airodump-ng to capture Wi-Fi data
sudo airodump-ng $MON_INTERFACE -w airfile -o csv
# Wait for airodump-ng to create the CSV file
#sleep $SLEEP_INTERVAL
# Publish CSV file to Kafka topic
kcat -b localhost:9092 -t wifi_data -P -l airfile-01.csv
# Remove the CSV file after publishing
#rm airfile-01.csv