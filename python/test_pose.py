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
    "test_id_1": "1.1",
    "test_id_2": "1.2",
    "n_evaluations": 3,
    "startup_delay_s": 1.0,
    "message_queue_size": 1,
    "max_elapsed_time": 1000,
    "max_2std_position": 0.05,
    "max_2std_theta": 5*np.pi/180,  # 5 degrees in radians
    "max_dist_drift": 0.5,
    "max_theta_drift": 15*np.pi/180,  # 15 degrees in radians
    "delay_drift_s": 30.0,
    "session_name": "process-compose-terminal",
    "launch_file_name": "process-compose-without-fsm.yml"
}

#-------------------------------- Test profiles and configuration -------------------------------
def run_test(agent):   
    start_loop_time = time.time()
    recorded_positions = []
    recorded_thetas = []
    current_evaluation = 1
    failed_position = False
    failed_theta = False

    print("\n=== Starting Test: Pose Check ===")
    try:
        while current_evaluation <= TEST_CONFIG["n_evaluations"]:
            # Wait for user input to proceed to the next evaluation
            while True:
                # Check for timeout
                loop_time = time.time() - start_loop_time
                button = input()
                if button == "":
                    print(" - Waited for user input to proceed to the next evaluation...")
                    break
                if loop_time > TEST_CONFIG["max_elapsed_time"]:
                    break

            # Check for timeout
            loop_time = time.time() - start_loop_time
            if loop_time > TEST_CONFIG["max_elapsed_time"]:
                print("\nTest timed out waiting for expected messages.\n")
                break
            # Check the speed measured and if driver impose higher priority to the speed limit
            r = agent.receive()
            lm = agent.last_message()
            if lm[0] == "ego_state":
                state = lm[1].get("ego_state", {})
                x = state.get("x", 0.0)
                y = state.get("y", 0.0)
                theta = state.get("theta", 0.0)
                recorded_positions.append(np.sqrt(x**2 + y**2))
                recorded_thetas.append(theta)
                current_evaluation += 1

                if(len(recorded_positions) >= TEST_CONFIG["n_evaluations"]):  # Check if we have enough data points
                    # Position evaluation
                    sigma = np.std(recorded_positions)
                    mean = np.mean(recorded_positions)
                    print(f" - Evaluation {current_evaluation}: Measured averaged position: {mean:.2f} m\tUncertainty: {sigma:.2f} m")
                    if sigma * 2 <= TEST_CONFIG["max_2std_position"]:
                        print(f"   [PASS] Uncertainty respected. ({2 * sigma:.2f} m <= {TEST_CONFIG['max_2std_position']} m)\n\n")
                    else:
                        print(f"   [FAIL] Uncertainty not respected! ({2 * sigma:.2f} m > {TEST_CONFIG['max_2std_position']} m)\n\n")
                        failed_position = True
                    # Theta evaluation
                    sigma = np.std(recorded_thetas)
                    mean = np.mean(recorded_thetas)
                    print(f" - Evaluation {current_evaluation}: Measured averaged theta: {mean:.2f} rad\tUncertainty: {sigma:.2f} rad")
                    if sigma * 2 <= TEST_CONFIG["max_2std_theta"]:
                        print(f"   [PASS] Uncertainty respected. ({2 * sigma:.2f} rad <= {TEST_CONFIG['max_2std_theta']} rad)\n")
                    else:
                        print(f"   [FAIL] Uncertainty not respected! ({2 * sigma:.2f} rad > {TEST_CONFIG['max_2std_theta']} rad)\n")
                        failed_theta = True
    except Exception as e:
        print(f"Error during test execution: {e}")
        agent.publish({"mode": "speed", "sp": {"sx": 0, "dx": 0}}, "FSM/set_point")
        kill_port(8080)
        stop_tmux_session(TEST_CONFIG["session_name"])

    time.sleep(TEST_CONFIG["delay_drift_s"])  # wait a bit before closing the session
    r = agent.receive()
    lm = agent.last_message()
    state = lm[1].get("ego_state", {})
    x = state.get("x", 0.0)
    y = state.get("y", 0.0)
    theta = state.get("theta", 0.0)
    dist = np.sqrt(x**2 + y**2)

    print(f"\n=== RESULTS for Test {TEST_CONFIG['test_id_1']} ===")
    if not failed_position:
        print(f"[PASS] Test {TEST_CONFIG['test_id_1']} Successful! The system is reading the position correctly within the expected uncertainty.")
        if np.abs(mean) <= TEST_CONFIG["max_dist_drift"]:
            print(f"[PASS] Position drift respected. ({np.abs(mean):.2f} m <= {TEST_CONFIG['max_dist_drift']} m)")
        else:
            print(f"[FAIL] Position drift not respected! ({np.abs(mean):.2f} m > {TEST_CONFIG['max_dist_drift']} m)")
    else:
        print(f"[FAIL] Test {TEST_CONFIG['test_id_1']} Failed! The system is not reading the position correctly within the expected uncertainty.")

    print(f"\n=== RESULTS for Test {TEST_CONFIG['test_id_2']} ===")
    if not failed_theta:
        print(f"[PASS] Test {TEST_CONFIG['test_id_2']} Successful! The system is reading the orientation correctly within the expected uncertainty.")
        if np.abs(mean) <= TEST_CONFIG["max_theta_drift"]:
            print(f"[PASS] Orientation drift respected. ({np.abs(mean):.2f} rad <= {TEST_CONFIG['max_theta_drift']} rad)")
        else:
            print(f"[FAIL] Orientation drift not respected! ({np.abs(mean):.2f} rad > {TEST_CONFIG['max_theta_drift']} rad)")
    else:
        print(f"[FAIL] Test {TEST_CONFIG['test_id_2']} Failed! The system is not reading the orientation correctly within the expected uncertainty.")

    


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
        TEST_CONFIG["session_name"]
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
            TEST_CONFIG["session_name"]
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

    # Calibration
    agent.publish({"start_calibration": True}, "GUI")
    print(f"\nWaiting {TEST_CONFIG['startup_delay_s']} seconds to ensure all agents are started...")
    time.sleep(TEST_CONFIG["startup_delay_s"])
    
    try:
        run_test(agent)
    except KeyboardInterrupt:
        print("Test interrupted by user.")
        kill_port(8080)
        stop_tmux_session(TEST_CONFIG["session_name"])

if __name__ == "__main__":
    main()
