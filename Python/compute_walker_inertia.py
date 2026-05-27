from mads_agent import Agent, EventType, MessageType, mads_version, mads_default_settings_uri
import time
import asyncio
import numpy as np
import plotext as plt
import subprocess
from datetime import datetime
from scipy.stats import normaltest
import math

wheel_radius = None
wheel_base = None
period = 0.1
fmt = "%Y-%m-%dT%H:%M:%S.%f%z"

def assess_normality(residuals, name="model", alpha=0.05):
    res = np.asarray(residuals).flatten()

    stat, p = normaltest(res)

    print()
    print(f"=== Normality check: {name} ===")
    print(f"statistic:\t{stat:.4f}")
    print(f"p-value:\t{p:.6g}")

    # Decision based on p-value
    if p > alpha:
        print("✔ Cannot reject normality (residuals look Gaussian)")
    else:
        print("✖ Reject normality (residuals are NOT Gaussian)")

    # Extra diagnostics (helpful for interpretation)
    mu = np.mean(res)
    sigma = np.std(res)
    print(f"mean:\t\t{mu:.4g}")
    print(f"std:\t\t{sigma:.4g}")

    # Heuristic guidance using the statistic (not a strict rule)
    if stat < 5:
        print("statistic small → close to Gaussian")
    elif stat < 20:
        print("statistic moderate → some deviation from Gaussian")
    else:
        print("statistic large → strong deviation from Gaussian")

    return stat, p

def plot_residuals_with_gaussian(residuals, title):
    res = residuals.flatten()

    mu = np.mean(res)
    sigma = np.std(res)

    # Histogram (normalized)
    hist, bin_edges = np.histogram(res, bins=30, density=True)
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])

    # Gaussian
    x = np.linspace(mu - 4*sigma, mu + 4*sigma, 200)
    gauss = (1 / (sigma * math.sqrt(2 * math.pi))) * np.exp(-0.5 * ((x - mu)/sigma)**2)

    plt.clf()
    plt.bar(bin_centers, hist)
    plt.plot(x, gauss)
    plt.title(title)
    plt.show()

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
    min_torque = -30
    max_torque = 30
    increment = 5
    step_function = False
    torque_walker = min_torque
    torque_walker_tmp = min_torque
    torque_wheel = T_walker2wheel(torque_walker)
    w_last = 0.0
    increasing = True
    n_iterations = 10
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

    b_np = np.array(b).reshape((n_acquisition, 1))

    # =========================
    # Case 1: fit both C and I
    # =========================

    params, *_ = np.linalg.lstsq(A_np, b_np, rcond=None)

    C_fit = params[0, 0]
    I_fit = params[1, 0]

    tau_pred_fit = A_np @ params
    res_fit = (b_np - tau_pred_fit).flatten()

    # =========================
    # Case 2: impose C, fit only I
    # =========================

    C_imposed = 19.75   # <-- put your known damping here

    omega = A_np[:, 0].reshape((-1, 1))
    alpha = A_np[:, 1].reshape((-1, 1))

    # tau - C*w = I*alpha
    b_reduced = b_np - C_imposed * omega

    I_imposed, *_ = np.linalg.lstsq(alpha, b_reduced, rcond=None)
    I_imposed = I_imposed[0, 0]

    tau_pred_imposed = C_imposed * omega + I_imposed * alpha
    res_imposed = (b_np - tau_pred_imposed).flatten()

    # =========================
    # Print results
    # =========================

    print()
    print("Model 1: fitted C and I")
    print(f"C fitted:\t{C_fit}")
    print(f"I fitted:\t{I_fit}")
    print(f"Residual mean:\t{np.mean(res_fit)}")
    print(f"Residual std:\t{np.std(res_fit)}")

    print()
    print("Model 2: imposed C, fitted I")
    print(f"C imposed:\t{C_imposed}")
    print(f"I fitted:\t{I_imposed}")
    print(f"Residual mean:\t{np.mean(res_imposed)}")
    print(f"Residual std:\t{np.std(res_imposed)}")

    # =========================
    # Normality tests
    # =========================

    assess_normality(res_fit, "Fit C & I", 0.3)
    assess_normality(res_imposed, "C imposed", 0.3)

    # =========================
    # Histogram comparison
    # =========================

    print()
    plot_residuals_with_gaussian(res_fit, "Residuals (fit C & I)")
    print()
    plot_residuals_with_gaussian(res_imposed, "Residuals (C imposed)")



asyncio.run(main())