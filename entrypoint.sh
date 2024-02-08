#!/bin/bash

# Check if the first argument is "bash"
if [ "$1" = "bash" ]; then
    exec "$@"
# Check if the first argument is "pawns"
elif [ "$1" = "pawns" ]; then
    shift
    exec pawns "$@"
# Check if there are any additional arguments
elif [ $# -gt 0 ]; then
    exec pawns "$@"
# Default to running python if there are no arguments
else
    exec python
fi
