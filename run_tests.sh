#!/bin/bash

# Loop through each file returned by `ls test`
for test in $(ls test); do
    echo "Running test: $test"
    python3 "test/$test"
    # Capture the exit code and stop the loop if a test fails
    if [ $? -ne 0 ]; then
        echo "Test $test failed. Stopping execution."
        exit 1
    fi
done

echo "All tests completed successfully."

