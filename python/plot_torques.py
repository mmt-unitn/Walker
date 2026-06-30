#!/home/miro/Walker/Python/.venv/bin/python3
import time
import json
from mads_agent import Agent, MessageType
import subprocess
import os
from pathlib import Path
import shutil
import serial
from serial import SerialException
from serial.tools import list_ports
import shlex
from session_utils import *
import numpy as np
import plotext as plt


TEST_CONFIG = {
    "test_id_1": "3",
    "test_id_2": "8.3",
    "speed_set": 1.0,
    "time_evaluation": 1.0,
    "time_between_evaluations": 3.0,
    "n_evaluations": 30000,
    "startup_delay_s": 1.0,
    "message_queue_size": 1,
    "max_elapsed_time": 50,
    "max_2std": 1,
    "speed_limit": 0.25,
    "wheel_radius": 0.084,
    "session_name": "process-compose-terminal",
    "launch_file_name": "process-compose-crypto.yml"
}


def plot_time_series(t_values, y_values, title, y_label):
    if len(t_values) == 0 or len(y_values) == 0:
        return

    print()
    plt.clf()
    plt.plot(t_values, y_values)
    plt.title(title)
    plt.xlabel("time [s]")
    plt.ylabel(y_label)
    plt.xscale("linear")
    plt.yscale("linear")
    plt.show()
    print()



#-------------------------------- Test profiles and configuration -------------------------------
def run_test(agent):   
    start_loop_time = time.time()
    recorded_torques = []
    recorded_torque_derivatives = []
    recorded_timecodes = []
    last_torque = 0.0
    current_evaluation = 0

    print("\n=== Recording Setpoints ===")
    try:
        while current_evaluation <= TEST_CONFIG["n_evaluations"]:
            r = agent.receive()
            lm = agent.last_message()
            if lm[0] == "FSM/set_point":
                sp = lm[1].get("sp", {})
                motor_torque = sp.get("sx", 0.0)
                timecode = lm[1].get("timecode", 0.0)

                torque_derivative = motor_torque - last_torque
                recorded_torques.append(motor_torque)
                recorded_torque_derivatives.append(torque_derivative)
                recorded_timecodes.append(timecode)
                last_torque = motor_torque

                current_evaluation = current_evaluation + 1

            
    except Exception as e:
        print(f"Error during test execution: {e}")
        stop_tmux_session(TEST_CONFIG["session_name"])
        kill_port(8080)

    
    plot_time_series(recorded_timecodes, recorded_torques, "Torque vs Time", "Torque [Nm]")
    plot_time_series(recorded_timecodes, recorded_torque_derivatives, "Torque Derivative vs Time", "Torque Derivative [Nm/s]")
    stop_tmux_session(TEST_CONFIG["session_name"])
    kill_port(8080)


#------------------------------- Main execution -------------------------------
def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    # derive config filename from this script's name: replace .py with .ini
    script_name = Path(__file__).stem
    config_filename = script_name + ".ini"
    config_file = repo_root / "config_files" / config_filename
    # copy the config file to the expected test
    shutil.copyfile(config_file, repo_root / "config_files" / "mads.ini")

    start_process_compose_session(
        repo_root,
        TEST_CONFIG["session_name"],
        TEST_CONFIG["launch_file_name"]
    )
    time.sleep(TEST_CONFIG["startup_delay_s"])

    # Initialize the agent
    agent = Agent(script_name)
    agent.set_id("python test agent")
     # Configure crypto settings
    agent.set_key_dir("/home/miro/security")
    agent.set_client_key_name("broker")
    agent.set_server_key_name("broker")
    agent.set_settings_timeout(10000)
    while agent.init(True) != 0:
        print("Cannot contact broker. Retrying...")
        print(f"ERROR: {agent.last_error()}")
        start_process_compose_session(
            repo_root,
            TEST_CONFIG["session_name"],
            TEST_CONFIG["launch_file_name"]
        )
        time.sleep(1)
    # set queue
    if agent.set_queue_size(TEST_CONFIG["message_queue_size"]) != 0:
        print(agent.last_error())
        exit()
    # Connect to the broker
    agent.connect()
    receive_timeout_ms = int(1000)
    agent.set_receive_timeout(max(receive_timeout_ms, 1))

    print(f"\nWaiting {TEST_CONFIG['startup_delay_s']} seconds to ensure all agents are started...")
    time.sleep(TEST_CONFIG["startup_delay_s"])
    # Calibration
    agent.publish({"start_calibration": True}, "GUI")
    
    try:
        run_test(agent)
    except KeyboardInterrupt:
        print("Test interrupted by user.")
        stop_tmux_session(TEST_CONFIG["session_name"])
        kill_port(8080)

if __name__ == "__main__":
    main()
