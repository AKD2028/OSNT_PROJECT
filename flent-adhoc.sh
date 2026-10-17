#!/bin/bash

#--------------------------- CONFIGURE PARAMETERS!!! ---------------------------


TOTAL_TEST_RUNS=3
TEST_LENGTH=10
NETSERVER_ADDRESS="10.0.0.2"
NUM_STREAMS=25
OUTPUT_DIR="results"

#--------------------------- CONFIGURE END -------------------------------------


#--------------------------- LOGIC ---------------------------

check_flent() {
    if command -v flent >/dev/null 2>&1; then
        return 0
    else
        echo "Error: flent is not installed..."
        return 1
    fi
}

installation_mac() {
    echo "Detected macOS"

    if ! command -v python3 &>/dev/null; then
        if ! command -v brew &>/dev/null; then
            echo "Homebrew is not installed. Please install it first!"
            exit 1
        fi
        brew install python3
    fi
    brew tap kris-anderson/netperf
    brew install netperf-enable-demo
    brew install fping
    pip3 install matplotlib --user
    pip3 install flent --user
    pip3 install pyqt5 qtpy --user
}

installation_ubuntu() {
    echo "Detected Ubuntu"

    sudo apt install netperf fping expect -y
    sudo apt install flent -y
}

install_flent() {
    if ! check_flent; then
        OS_NAME="$(uname -s)"
        case "${OS_NAME}" in
            Darwin*)
                # macOS kernel is Darwin
                installation_mac
                ;;
            Linux*)
                # Check /etc/os-release for the specific distribution
                if [ -f /etc/os-release ]; then
                    # Source the os-release file
                    . /etc/os-release
                    if [ "$ID" = "ubuntu" ]; then
                        installation_ubuntu
                    else
                        echo "Error: Detected Linux, but distro is not Ubuntu (ID: $ID)."
                        exit 1
                    fi
                else
                    echo "Error: /etc/os-release not found. Cannot determine the distro."
                    exit 1
                fi
                ;;
            *)
                echo "Error: Unsupported operating system (${OS_NAME})."
                exit 1
                ;;
        esac
    fi
}

# Robustness logic: checkpointing, retries...
CHECKPOINT_FILE="${OUTPUT_DIR}/.checkpoint"
mkdir -p "$OUTPUT_DIR"
touch "$CHECKPOINT_FILE"
MAX_RETRIES=3
RETRY_DELAY=10

is_done() {
    grep -Fxq "$1" "$CHECKPOINT_FILE"
}

mark_done() {
    echo "$1" >> "$CHECKPOINT_FILE"
}

validate_csv() {
    local file="$1"
    [[ -s "$file" ]] || return 1
    local lines
    lines=$(wc -l < "$file")
    [[ "$lines" -ge 2 ]] || return 1
    return 0
}

run_test_safely() {
    local key="$1"; shift
    local out_file="$1"; shift

    if is_done "$key"; then
        echo "Skipping already-completed test: $key"
        return 0
    fi

    local attempt=1
    while (( attempt <= MAX_RETRIES )); do
        echo "Running: $key (attempt $attempt/$MAX_RETRIES)"
        "$@"
        local status=$?

        if [[ $status -eq 0 ]] && validate_csv "$out_file"; then
            mark_done "$key"
            echo "Completed: $key"
            return 0
        fi

        echo "Failed or invalid CSV for $key (exit=$status). Removing partial file and retrying..."
        rm -f "$out_file"
        attempt=$((attempt + 1))
        [[ $attempt -le $MAX_RETRIES ]] && sleep "$RETRY_DELAY"
    done

    echo "ERROR: $key failed after $MAX_RETRIES attempts."
    return 1
}


run_flent_test() {
    local iter="$1"
    local length="$2"
    local address="$3"
    local output_dir="$4"
    local n="$NUM_STREAMS"


    RRUL_DIR="$output_dir/rrul"
    mkdir -p "$RRUL_DIR"
    RRUL_OUT="$RRUL_DIR/${iter}-rrul_${length}"
    RRUL_KEY="${iter}:rrul"

    # RRUL TEST
    echo -e "Running rrul test for length=$length, with iter=$iter...\n"

    run_test_safely "$RRUL_KEY" "$RRUL_OUT" \
        flent rrul -H "$address" --length="$length" -f csv --output="$RRUL_OUT"
    if [[ $? -ne 0 ]]; then
        echo "Aborting run_flent_test for iter=$iter (rrul stage failed). Re-run to resume."
        return 1
    fi

    TCP_NDOWN_DIR="$output_dir/tcp_${n}down"
    mkdir -p "$TCP_NDOWN_DIR"
    TCP_NDOWN_OUT="$TCP_NDOWN_DIR/${iter}-tcp_${n}down_${length}"
    TCP_NDOWN_KEY="${iter}:tcp_${n}down"

    echo $TCP_NDOWN_OUT
    echo $TCP_NDOWN_KEY

    # TCP_NDOWN Test
    echo -e "\nRunning tcp_ndown test for length=$length, with streams=$n, iter=$iter \n"

    run_test_safely "$TCP_NDOWN_KEY" "$TCP_NDOWN_OUT" \
        flent tcp_ndown --test-parameter=download_streams="$n" -H "$address" --length="$length" -f csv --output="$TCP_NDOWN_OUT"
    if [[ $? -ne 0 ]]; then
        echo "Aborting run_flent_test for iter=$iter (tcp_${n}down stage failed). Re-run to resume."
        return 1
    fi

    TCP_NUP_DIR="$output_dir/tcp_${n}up"
    mkdir -p "$TCP_NUP_DIR"
    TCP_NUP_OUT="$TCP_NUP_DIR/${iter}-tcp_${n}up_${length}"
    TCP_NUP_KEY="${iter}:tcp_${n}up"

    # TCP_NUP Test
    echo -e "\nRunning tcp_nup test for length=$length, with streams=$n, iter=$iter \n"

    run_test_safely "$TCP_NUP_KEY" "$TCP_NUP_OUT" \
        flent tcp_nup --test-parameter=upload_streams="$n" -H "$address" --length="$length" -f csv --output="$TCP_NUP_OUT"
    if [[ $? -ne 0 ]]; then
        echo "Aborting run_flent_test for iter=$iter (tcp_${n}up stage failed). Re-run to resume."
        return 1
    fi
}

#------------------------------ LOGIC END -------------------------------


#--------------------------- Essential Script ---------------------------

install_flent

for (( i = 1; i <= $TOTAL_TEST_RUNS; i++ )); do
    if is_done "${i}:DONE"; then
        echo "Skipping already-completed iteration: $i"
        continue
    fi

    run_flent_test "$i" "$TEST_LENGTH" "$NETSERVER_ADDRESS" "$OUTPUT_DIR"
    flent_status=$?
    if [[ $flent_status -ne 0 ]]; then
        echo "Error: flent test failed during iteration=$i."
        echo "Progress so far is saved in $CHECKPOINT_FILE."
        echo "Fix the connection issue and re-run this script to resume."
        exit 1
    fi
	echo -e "Finished a test suite $i times\n"
done

echo -e "All tests completed\n"

#---------------------------- End of Script -----------------------------


