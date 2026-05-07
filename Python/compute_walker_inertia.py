from mads_agent import Agent, EventType, MessageType, mads_version, mads_default_settings_uri
import time
import asyncio
import numpy as np
import plotext as plt
import subprocess
from datetime import datetime

wheel_radius = None
wheel_base = None
period = 0.1
fmt = "%Y-%m-%dT%H:%M:%S.%f%z"

async def listen():
    await asyncio.to_thread(input, "Press ENTER to stop\n")

async def loop_control(time_s):
    await asyncio.sleep(time_s)

def T_walker2wheel(torque_walker):
    return torque_walker * wheel_radius / (wheel_base / 2)

async def main():
    # deactivate FSM
    result = subprocess.run(["sudo", "systemctl", "stop", "mads-fsm.service"], capture_output=True, text=True)
    print(result.stdout)   # command output
    print(result.stderr)   # errors (if any)

    # Initialize the agent
    agent = Agent("walker_inertia") 
    agent.set_id("python")

    # Crypto
    agent.set_key_dir("/home/miro/security")
    agent.set_client_key_name("broker")
    agent.set_server_key_name("broker")

    # Wait for the broker
    agent.set_settings_timeout(2000) # 2 sec timeout
    while agent.init(True) != 0:
        print("Cannot contact broker\n")

    # Initialize variables
    print(agent.settings()) # received from the broker
    # Extract json informations
    json_sett = agent.settings()
    global wheel_radius
    global wheel_base
    wheel_radius = json_sett["wheel_radius"]
    wheel_base = json_sett["wheel_base"]
    if agent.set_queue_size(1) != 0:
        print(agent.last_error())
        exit()
    agent.connect()
    agent.set_receive_timeout(int(period*1000 - 2)) # Timeout for receiving messages, in ms
    agent.set_queue_size(1)
    
    # Aquire data
    min_torque = -50
    max_torque = 50
    increment = 10
    step_function = False
    torque_walker = min_torque
    torque_walker_tmp = min_torque
    torque_wheel = T_walker2wheel(torque_walker)
    w_last = 0.0
    increasing = True
    n_iterations = 25
    time_imu_previous = datetime.now().astimezone()
    time_imu_current = datetime.now().astimezone()
    A = []
    b = []

    stop_task = asyncio.create_task(listen())
    while(not stop_task.done()):
        # start a task to control time period
        task = asyncio.create_task(loop_control(period))

        # Publishing
        msg = {"mode": "torque", "sp": {"dx": torque_wheel * 0, "sx": -torque_wheel * 100}}
        agent.publish(msg, "FSM/set_point")

        await task  # wait for it to finish

        # Receiving
        r = agent.receive()
        if r == MessageType.NONE:
            print("No message received\n")
            continue
        else:
            lm = agent.last_message()
            if(lm[0] == "imu"):
                w_current = -(lm[1])["gyro"][2]
                time_stp = datetime.strptime((lm[1])["timestamp"]["$date"], fmt)
                delta_t = (time_stp - time_imu_previous).total_seconds()
                time_imu_previous = time_stp
                alpha_current = (w_current - w_last) / delta_t
                w_last = w_current
                # Update A and b only if the angular velocity is significant, to avoid noise
                if(abs(w_current) > 0.001):
                    A.append([w_current, alpha_current])
                    b.append(torque_walker)

        # Change torque
        if(torque_walker > max_torque) and increasing:
            increasing = False
        elif(torque_walker < min_torque) and (not increasing):
            increasing = True
            # it stops automatically after n_iterations
            n_iterations -= 1
            print(f"number of iterations left:\t{n_iterations}")
            if n_iterations == 0:
                break

        if increasing:
            torque_walker_tmp += increment
        else:
            torque_walker_tmp -= increment
        if(not step_function):
            torque_walker = torque_walker_tmp
        else:
            if increasing:
                torque_walker = max(torque_walker_tmp, max_torque)
            else:
                torque_walker = min(torque_walker_tmp, min_torque)

        torque_wheel = T_walker2wheel(torque_walker)


    msg = {"mode": "torque", "sp": {"dx": 0 * 100, "sx": -0 * 100}}
    agent.publish(msg, "FSM/set_point")
    agent.disconnect()

    # activate FSM
    result = subprocess.run(["sudo", "systemctl", "start", "mads-fsm.service"], capture_output=True, text=True)
    print(result.stdout)   # command output
    print(result.stderr)   # errors (if any)

    # LMS to find parameters
    A_np = np.array(A)
    n_acquisition = A_np.shape[0]

    T_vec = np.array(b).reshape((n_acquisition, 1))

    params = np.linalg.inv(A_np.T @ A_np) @ A_np.T @ T_vec
    I = params[1]
    C = params[0]

    print()
    print("Estimated model:")
    print("torque = I * alpha + B * omega")
    print()
    print(f"Inertia I:\t\t{I}")
    print(f"Viscous damping C:\t{C}")
    print()

    C_forced = 19
    print(f"Imposing the value of dumping to {C_forced}")
    w = A_np[:, 0:1]  
    new_T_vec = T_vec - w * C_forced
    new_A_np = A_np[:, 1:2]  
    params = np.linalg.inv(new_A_np.T @ new_A_np) @ new_A_np.T @ new_T_vec
    print()
    print("Estimated model:")
    print(f"torque = I * alpha + {C_forced} * omega")
    print()
    print(f"Inertia I:\t\t{params[0]}")



asyncio.run(main())