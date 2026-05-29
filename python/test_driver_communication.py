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
from session_utils import start_process_compose_session


TEST_CONFIG = {
    "test_id": "7.3",
    "startup_delay_s": 1.0,
    "message_queue_size": 50,
    "port": "/dev/drivers",
    "max_elapsed_time_ms": 500,
    "session_name": "process-compose-terminal",
}

#-------------------------------- Test profiles and configuration -------------------------------
def run_test(agent):   
    ser = serial.Serial(TEST_CONFIG["port"], 115200, timeout=1)
    elapsed_time = None
    driver_timecode = None
    portenta_timecode = None
    fsm_timecode = None
    driver_available = False
    FSM_available = False
    start_loop_time = time.time()

    print("\n=== Starting Test: Driver Communication Failure Handling ===")
    try:
        while True:
            loop_time = time.time() - start_loop_time
            if loop_time > 10:
                elapsed_time = float('inf')
                print("\nTest timed out waiting for expected messages.\n")
                break
            r = agent.receive()
            lm = agent.last_message()

            if lm[0] == "FSM/portenta" and driver_available and FSM_available:
                command = lm[1].get("cmd", {})
                portenta_timecode = lm[1].get("timecode", {})
                if "red" in str(command):
                    elapsed_time = portenta_timecode - fsm_timecode
                    print(f" - Received expected command after failure: {command}. Elapsed time: {elapsed_time:.10f}s\n")
                    break
            elif lm[0] == "driver" and "encoders" in lm[1] and not driver_available:
                driver_timecode = lm[1].get("timecode", {})
                if(driver_timecode is not None):
                    driver_available = True
                    print(" - driver communication is working\n")
            elif lm[0] == "FSM/set_point" and driver_available and not FSM_available:
                fsm_timecode = lm[1].get("timecode", {})
                if(fsm_timecode is not None and fsm_timecode >= driver_timecode):
                    FSM_available = True
                    print(" - FSM is ready to recognize failure, simulating failure by closing the serial port...\n")
                    # simulate failure
                    ser.close()

    except Exception as e:
        print(f"Error during test execution: {e}")
        # later reconnect
        ser.open()
    
    except SerialException as e:
        msg = str(e).lower()
        if "could not open port" in msg or "no such file or directory" in msg:
            print("Port not recognized / not present:", e)
        else:
            print("Serial error:", e)
        ports = list_ports.comports()
        print("Available ports:", [p.device for p in ports])

    # later reconnect
    #ser.open()

    print(f"\n=== RESULTS for Test {TEST_CONFIG['test_id']} ===")
    if elapsed_time > TEST_CONFIG["max_elapsed_time_ms"] / 1000.0:
        print(f"[FAIL] Test {TEST_CONFIG['test_id']} Failed! Elapsed time {elapsed_time:.5f}s is too long, indicating improper handling of the failure.")
    else:
        print(f"[PASS] Test {TEST_CONFIG['test_id']} Successful! Elapsed time {elapsed_time:.5f}s indicates proper handling of the failure.")

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


if __name__ == "__main__":
    main()
