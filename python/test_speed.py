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


TEST_CONFIG = {
    "test_id_1": "3",
    "test_id_2": "8.3",
    "speed_set": 1.0,
    "time_evaluation": 1.0,
    "time_between_evaluations": 3.0,
    "n_evaluations": 10,
    "startup_delay_s": 1.0,
    "message_queue_size": 1,
    "max_elapsed_time": 50,
    "max_2std": 1,
    "speed_limit": 0.25,
    "wheel_radius": 0.084,
    "session_name": "process-compose-terminal",
    "launch_file_name": "process-compose-without-fsm.yml"
}

#-------------------------------- Test profiles and configuration -------------------------------
def run_test(agent):   
    start_loop_time = time.time()
    recorded_speeds = []
    current_evaluation = 1
    failed_speed_limit = False
    failed_uncertainty = False

    print("\n=== Starting Test: Speed Check ===")
    try:
        while current_evaluation <= TEST_CONFIG["n_evaluations"]:
            # Check for timeout
            loop_time = time.time() - start_loop_time
            if loop_time > TEST_CONFIG["max_elapsed_time"]:
                elapsed_time = float('inf')
                print("\nTest timed out waiting for expected messages.\n")
                break
            # Send command to set speed higher than the limit
            sign = 1 if current_evaluation % 2 == 0 else -1
            speed_rev_per_min = (TEST_CONFIG["speed_set"] / (2 * np.pi * TEST_CONFIG["wheel_radius"])) * 60
            agent.publish({"mode": "speed", "sp": {"sx": sign * speed_rev_per_min, "dx": sign * speed_rev_per_min}}, "FSM/set_point")
            # Check the speed measured and if driver impose higher priority to the speed limit
            r = agent.receive()
            lm = agent.last_message()
            if lm[0] == "ego_state":
                state = lm[1].get("ego_state", {})
                v = state.get("speed", 0.0)
                recorded_speeds.append(v)
                if(loop_time > TEST_CONFIG["time_evaluation"] * current_evaluation + TEST_CONFIG["time_between_evaluations"] * (current_evaluation - 1)):
                    sigma = np.std(recorded_speeds)
                    mean_speed = np.mean(recorded_speeds)
                    print(f" - Evaluation {current_evaluation}: Measured speed: {mean_speed:.2f} m/s\tUncertainty: {sigma:.2f} m/s")
                    if np.abs(mean_speed) <= TEST_CONFIG["speed_limit"]:
                        print(f"   [PASS] Speed limit respected. ({np.abs(mean_speed):.2f} m/s <= {TEST_CONFIG['speed_limit']} m/s)")
                    else:
                        print(f"   [FAIL] Speed limit not respected! ({np.abs(mean_speed):.2f} m/s > {TEST_CONFIG['speed_limit']} m/s)")
                        failed_speed_limit = True
                        break
                    if sigma * 2 <= TEST_CONFIG["max_2std"]:
                        print(f"   [PASS] Uncertainty respected. ({2 * sigma:.2f} m/s <= {TEST_CONFIG['max_2std']} m/s)\n")
                    else:
                        print(f"   [FAIL] Uncertainty not respected! ({2 * sigma:.2f} m/s > {TEST_CONFIG['max_2std']} m/s)\n")
                        failed_uncertainty = True
                        break
                    current_evaluation += 1
                    agent.publish({"mode": "speed", "sp": {"sx": 0, "dx": 0}}, "FSM/set_point")
                    time.sleep(TEST_CONFIG["time_between_evaluations"])  # wait a bit before the next evaluation
                    recorded_speeds = []  # reset recorded speeds for the next evaluation
    except Exception as e:
        print(f"Error during test execution: {e}")
        agent.publish({"mode": "speed", "sp": {"sx": 0, "dx": 0}}, "FSM/set_point")
        kill_port(8080)
        stop_tmux_session(TEST_CONFIG["session_name"])

    agent.publish({"mode": "speed", "sp": {"sx": 0, "dx": 0}}, "FSM/set_point")
    print(f"\n=== RESULTS for Test {TEST_CONFIG['test_id_1']} ===")
    if not failed_uncertainty:
        print(f"[PASS] Test {TEST_CONFIG['test_id_1']} Successful! The system is reading the speed correctly within the expected uncertainty.")
    else:
        print(f"[FAIL] Test {TEST_CONFIG['test_id_1']} Failed! The system is not reading the speed correctly within the expected uncertainty.")
    
    print(f"\n=== RESULTS for Test {TEST_CONFIG['test_id_2']} ===")
    if not failed_speed_limit:
        print(f"[PASS] Test {TEST_CONFIG['test_id_2']} Successful! The system is applying the speed limit correctly, even when commanded to go faster.")
    else:
        print(f"[FAIL] Test {TEST_CONFIG['test_id_2']} Failed! The system is not applying the speed limit correctly.")

    kill_port(8080)
    stop_tmux_session(TEST_CONFIG["session_name"])


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
    agent.set_settings_timeout(10000)
    while agent.init(False) != 0:
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
        kill_port(8080)
        stop_tmux_session(TEST_CONFIG["session_name"])

if __name__ == "__main__":
    main()
