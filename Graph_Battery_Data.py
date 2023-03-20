#! /data/data/com.termux/files/usr/bin/python

# -------------------------------------- Imports --------------------------------------

import argparse  # argparse is used to parse command line arguments for the script
from datetime import datetime  # datetime allows a convenient way to store timestamps
import json  # json library is used to parse the output from "termux-battery-status"
from pathlib import Path  # pathlib allows a convenient way to handle paths
import subprocess  # subprocess allows running a command and capturing the output
from termcolor import cprint  # termcolor allows easy printing of coloured text
import time  # time has a simple .sleep() function for basic time delays
from tqdm import tqdm  # tqdm is used to create a progress bar
import matplotlib.pyplot as plt  # matplotlib allows creation of graphs

# -------------------------------------------------------------------------------------

# ---------------------------------- Argument Parser ----------------------------------
# Set up the argument parser to retreive inputs from the user
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    "-p",
    "--percentage",
    dest="stop_percentage",
    help="The percentage at which the script should stop recording.",
    type=int,
    required=False,
    default=100,
    choices=range(0, 100),
    metavar="[0-100]",
)
parser.add_argument(
    "-t",
    "--time",
    dest="stop_time",
    help="The time (in seconds) after which the script should stop recording.",
    type=int,
    required=False,
    choices=range(0, 259200),
    metavar="[0-259200]",
)
parser.add_argument(
    "-i",
    "--interval",
    dest="time_interval",
    help="The desired time (in milliseconds) between measurements.",
    type=int,
    default=1000,
    choices=range(0, 1800000),
    metavar="[0-1800000]",
)
parser.add_argument(
    "-o",
    "--output-file",
    dest="output_file",
    help="Path to the output .jpg file.",
    type=Path,
    required=False,
    default=f"./Battery_Statistics_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg",
)
parser.add_argument(
    "-v",
    "--verbose",
    dest="verbose",
    help="Print verbose messages.",
    action="store_true",
)

# Parse the user inputs using the argument parser
args = parser.parse_args()
# -------------------------------------------------------------------------------------


# --------------------------------- Input Validation ----------------------------------
# Check if both a stop_percentage and stop_time have been specified. If they have, warn
# the user that whichever is reached first takes president.
if (args.stop_time is not None) and (args.stop_percentage != 100):
    cprint(
        "[WARN] Both a percentage and time have been specified. Whichever is reached "
        + "first will cause the program to terminate.",
        "yellow",
    )
# -------------------------------------------------------------------------------------

# This will be used to track the monitoring progress
last_progress = 0
current_progress = 0

# This records the time at which the script started for relative timings
start_time = datetime.now()

# These are the statistics that will be monitored
timestamp = []
percentage = []
temperature = []
current = []

# If verbose is specifed, print output that the loop is starting
if args.verbose:
    cprint("[VERBOSE] Starting monitoring loop...", "blue")

with tqdm(total=100, unit="%") as progress:
    while current_progress < 100:
        # Get output from termux-battery-status command
        with subprocess.Popen(
            ["termux-battery-status"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ) as proc:
            # Parse the command output as json and record the time
            output = proc.stdout.read().decode("utf-8")
            current_status = json.loads(output)
            current_time = datetime.now()

            # Calculate the current progress from the specified stop conditions
            current_progress = int(current_status["percentage"])
            if args.stop_time is not None:
                time_progress = int(
                    ((current_time - start_time).total_seconds() / args.stop_time) * 100
                )
                current_progress = min(max(time_progress, current_progress), 100)
            if args.verbose:
                cprint(f"[VERBOSE] Current progress: {current_progress}", "blue")

            # Update the progress bar
            progress.update(current_progress - last_progress)

            # Record the relevant statistics
            timestamp.append((current_time - start_time).total_seconds())
            percentage.append(int(current_status["percentage"]))
            temperature.append(float(current_status["temperature"]))
            # Reverse current sign as Termux-API convention is negative for charging
            current.append(-float(int(current_status["current"]) / 1000))

            last_progress = current_progress

            # Wait to take next reading
            sleep_time = (
                timedelta(milliseconds=args.time_interval)
                - (datetime.now() - current_time)
            ).total_seconds()
            time.sleep(sleep_time)

if args.verbose:
    cprint("[VERBOSE] Monitoring loop finished.", "blue")

# After the loop ends, create plots with the given data
if len(current) > 0:
    # Create a plot with 3 subplots (percentage, temperature, current)
    figure, axis = plt.subplots(3, sharex=True)

    # Add a title to the plot
    figure.suptitle("Charging Statistics", size=20)

    # Create the battery percentage plot
    axis[0].plot(timestamp, percentage, "tab:blue")
    axis[0].set(title="Battery Percentage", ylabel="Percentage/%")

    # Create the battery current plot
    axis[1].plot(timestamp, current, "tab:orange")
    axis[1].set(title="Battery Current", ylabel="Current/mA")

    # Create the battery temperature plot
    axis[2].plot(timestamp, temperature, "tab:red")
    axis[2].set(
        title="Battery Temperature", xlabel="Time/s", ylabel="Temperature/$^\circ$C"
    )

    figure.tight_layout()

    cprint(f"[INFO] Saving output to {args.output_file.resolve()}", "green")
    plt.savefig(args.output_file)
