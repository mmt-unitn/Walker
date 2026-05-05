from mads_agent import Agent, EventType, MessageType, mads_version, mads_default_settings_uri
import time
import asyncio
import numpy as np
import plotext as plt

wheel_radius = None
wheel_base = None
period = 0.05

async def listen():
    await asyncio.to_thread(input, "Press ENTER to stop\n")

async def loop_control(time_s):
    await asyncio.sleep(time_s)

async def find_C(agent):
    torque_walker = 15
    torque_wheel = torque_walker * wheel_radius / (wheel_base / 2)
    list_of_w = []
    stop_task = asyncio.create_task(listen())
    converged = 0
    converged_values = []
    th = 0.065
    list_of_w_conv = []
    list_of_T = []
    n_elements = 20
    time_sleep = 3

    while(converged < 5 and not stop_task.done()):
        task = asyncio.create_task(loop_control(period))

        # Receiving
        r = agent.receive()
        if r == MessageType.NONE:
            print("No message received\n")
        else:
            lm = agent.last_message()
            if(lm[0] == "imu"):
                w_current = -(lm[1])["gyro"][2]
                if(len(list_of_w) < n_elements):
                    list_of_w.append(w_current)
                elif abs(w_current) > 0.03:
                    list_of_w.pop(0)
                    list_of_w.append(w_current)
                    if max(list_of_w) - min(list_of_w) < th: # constant speed
                        list_of_T.append(torque_walker)
                        list_of_w_conv.append(w_current)
                        converged = converged + 1
                        converged_values.append(torque_wheel / w_current)
                        print(f"converged #{len(converged_values)}")
                        print("converged values:\t", converged_values)
                        torque_walker = torque_walker + 5
                        torque_wheel = torque_walker * wheel_radius / (wheel_base / 2)
                        list_of_w = []
                        msg = {"mode": "torque", "sp": {"dx": torque_wheel * 0, "sx": -torque_wheel * 100}}
                        agent.publish(msg, "FSM/set_point")
                        time.sleep(time_sleep)

        if len(list_of_w) == n_elements - 1:
            time.sleep(time_sleep)
        # Publishing
        msg = {"mode": "torque", "sp": {"dx": torque_wheel * 0, "sx": -torque_wheel * 100}}
        agent.publish(msg, "FSM/set_point")

        await task  # wait for it to finish

    # Show results
    plt.scatter(converged_values)  # or plt.scatter(x, y)
    plt.show()

    plt.scatter(list_of_T)  # or plt.scatter(x, y)
    plt.show()

    plt.scatter(list_of_w_conv)  # or plt.scatter(x, y)
    plt.show()



async def main():
    agent = Agent("walker_inertia") 
    agent.set_id("python")

    # Crypto
    agent.set_key_dir("/home/miro/security")
    agent.set_client_key_name("broker")
    agent.set_server_key_name("broker")

    agent.set_settings_timeout(2000) # 2 sec timeout
    while agent.init(True) != 0:
        print("Cannot contact broker\n")

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

    # Step 1
    await find_C(agent)

    # Safety stop
    stop_task = asyncio.create_task(listen())
    while(not stop_task.done()):
        msg = {"mode": "torque", "sp": {"dx": 0 * 100, "sx": -0 * 100}}
        agent.publish(msg, "FSM/set_point")
    
    # Step 2
    torque_walker = 70
    torque_wheel = torque_walker * wheel_radius / wheel_base
    A = []
    w_last = 0.0

    stop_task = asyncio.create_task(listen())
    while(not stop_task.done()):
        task = asyncio.create_task(loop_control(period))

        # Receiving
        r = agent.receive()
        if r == MessageType.NONE:
            print("No message received\n")
        else:
            lm = agent.last_message()
            if(lm[0] == "imu"):
                w_current = (lm[1])["gyro"][2]
                alpha_current = (w_current - w_last) / (period)
                A.append([w_current, alpha_current])
                w_last = w_current

        # Publishing
        msg = {"mode": "torque", "sp": {"dx": torque_wheel * 0, "sx": -torque_wheel * 100}}
        agent.publish(msg, "FSM/set_point")

        await task  # wait for it to finish

    msg = {"mode": "torque", "sp": {"dx": 0 * 100, "sx": -0 * 100}}
    agent.publish(msg, "FSM/set_point")
    agent.disconnect()

    A_np = np.array(A)
    n_acquisition = A_np.shape[0]

    T_vec = np.ones((n_acquisition, 1)) * torque_walker

    params = np.linalg.inv(A_np.T @ A_np) @ A_np.T @ T_vec
    print(f"Dumping found:\t{-params[0]}")
    print(f"Inertia found:\t{params[1]}")



asyncio.run(main())