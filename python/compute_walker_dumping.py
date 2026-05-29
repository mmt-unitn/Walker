"""
compute_walker_dumping.py

This script estimates the viscous damping coefficient (C) of the Walker system
by applying constant torques and measuring the resulting steady-state angular velocities.
It uses the MADS agent framework to communicate with the Walker's FSM and IMU.

The damping coefficient is calculated as C = torque / omega, where omega is the
steady-state angular velocity for a given torque.
"""

from mads_agent import Agent, EventType, MessageType, mads_version, mads_default_settings_uri
import time
import asyncio
import numpy as np
import plotext as plt

# Global variables for wheel parameters (set from agent settings)
wheel_radius = None
wheel_base = None
period = 0.01  # Control loop period in seconds


async def listen():
    """
    Asynchronous function to listen for user input to stop the program.
    Waits for ENTER key press.
    """
    await asyncio.to_thread(input, "Press ENTER to stop\n")


async def loop_control(time_s):
    """
    Asynchronous sleep function for controlling loop timing.

    Args:
        time_s (float): Time to sleep in seconds.
    """
    await asyncio.sleep(time_s)


def torque_walker_to_wheel(torque_walker):
    """
    Convert walker torque to wheel torque.

    Args:
        torque_walker (float): Torque in walker coordinates.

    Returns:
        float: Torque in wheel coordinates.
    """
    return torque_walker * wheel_radius / (wheel_base / 2)


async def find_C(agent):
    """
    Main function to find the damping coefficient C by applying increasing torques
    and waiting for steady-state angular velocities.

    Args:
        agent (Agent): The MADS agent instance for communication.

    The function:
    - Starts with an initial torque
    - Monitors IMU data for steady-state conditions
    - Increments torque when convergence is detected
    - Collects C values and displays statistics
    """
    torque_walker = 15  # Initial torque value
    torque_wheel = torque_walker_to_wheel(torque_walker)
    list_of_w = []  # Buffer for recent angular velocities
    stop_task = asyncio.create_task(listen())
    converged = 0  # Counter for convergence detections
    converged_values = []  # List of calculated C values
    th = 0.07  # Threshold for steady-state detection (max - min < th)
    list_of_w_conv = []  # Converged angular velocities
    list_of_T = []  # Corresponding torques
    n_elements = 50  # Number of samples to check for steady-state
    time_sleep = 3  # Sleep time after torque change

    while converged < 5 and not stop_task.done():
        # Control loop timing
        task = asyncio.create_task(loop_control(period))

        # Receive IMU data
        r = agent.receive()
        if r == MessageType.NONE:
            print("No message received\n")
        else:
            lm = agent.last_message()
            if lm[0] == "imu":
                w_current = -(lm[1])["gyro"][2]  # Angular velocity from IMU (z-axis, negated)

                # Maintain a rolling buffer of angular velocities
                if len(list_of_w) < n_elements:
                    list_of_w.append(w_current)
                elif abs(w_current) > 0.01:  # Only process if velocity is significant
                    list_of_w.pop(0)
                    list_of_w.append(w_current)

                    # Check for steady-state (constant speed)
                    if max(list_of_w) - min(list_of_w) < th:
                        list_of_T.append(torque_walker)
                        list_of_w_conv.append(w_current)
                        converged += 1
                        c_value = torque_walker / w_current  # Calculate damping coefficient
                        converged_values.append(c_value)
                        print(f"Converged #{len(converged_values)}")
                        print("Converged values:\t", converged_values)
                        print(f"Torque: {torque_walker}\tWheel: {torque_wheel}\tOmega: {w_current}\n")

                        # Increment torque for next iteration
                        torque_walker += 5
                        torque_wheel = torque_walker_to_wheel(torque_walker)
                        list_of_w = []  # Reset buffer

                        # Publish new torque setpoint
                        msg = {"mode": "torque", "sp": {"dx": torque_wheel * 0, "sx": -torque_wheel * 100}}
                        agent.publish(msg, "FSM/set_point")
                        time.sleep(time_sleep)  # Allow system to settle

        # Publish current torque setpoint
        msg = {"mode": "torque", "sp": {"dx": torque_wheel * 0, "sx": -torque_wheel * 100}}
        agent.publish(msg, "FSM/set_point")

        await task  # Wait for loop period

    # Display results
    print()

    # Plot converged values (if in interactive environment)
    plt.scatter(converged_values)
    plt.show()

    print()
    print("Median C:\t", np.median(converged_values))
    print("Std C:\t", np.std(converged_values))


async def main():
    """
    Main entry point for the script.
    Initializes the MADS agent, connects to the broker, and runs the damping estimation.
    """
    # Initialize agent
    agent = Agent("walker_dumping")
    agent.set_id("python")

    # Configure crypto settings
    agent.set_key_dir("/home/miro/security")
    agent.set_client_key_name("broker")
    agent.set_server_key_name("broker")

    # Wait for broker connection
    agent.set_settings_timeout(2000)  # 2 sec timeout
    while agent.init(True) != 0:
        print("Cannot contact broker\n")

    # Print received settings
    print(agent.settings())

    # Extract wheel parameters from settings
    json_sett = agent.settings()
    global wheel_radius
    global wheel_base
    wheel_radius = json_sett["wheel_radius"]
    wheel_base = json_sett["wheel_base"]

    # Configure agent
    if agent.set_queue_size(1) != 0:
        print(agent.last_error())
        exit()
    agent.connect()
    agent.set_receive_timeout(int(period * 1000 - 2))  # Timeout in ms
    agent.set_queue_size(1)

    # Run damping estimation
    await find_C(agent)


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())