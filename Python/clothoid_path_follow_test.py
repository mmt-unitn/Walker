#!/home/miro/Walker/Python/.venv/bin/python3
"""Run the clothoid path-following requirement test (Req. ID 13).

This script sends the path-following command to the same GUI topic, records
FSM path-planning feedback, and checks whether the walker stays within the
required 2 m offset from the standard clothoid path AND actually traverses
it (so a stationary walker cannot accidentally pass the test).

The acceptance criteria are:
  1. The recorded walker trajectory is everywhere within MAX_ALLOWED_OFFSET_M
     of the commanded clothoid path.
  2. The walker actually followed the path: it reached within
     MIN_FINAL_DISTANCE_M of (4, 4) AND its projection onto the path covered
     at least MIN_PROGRESS_RATIO of the path arc length.
  3. The run completed normally (FSM mode transition or quiet-after-active),
     not by hard timeout.
  4. Raising the torsional stiffness K_w from 25 to 50 Nm/rad reduces the
     maximum offset by at least HIGH_STIFFNESS_MARGIN_M (so sub-mm noise
     does not flip the verdict run to run).
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import time


# FSM listens for GUI commands on this topic. This matches test_impedance_control.py.
GUI_TOPIC = "GUI"

# FSM/path_planning and FSM/mode are the evidence streams. driver and ego_state
# are diagnostics that explain why the FSM may refuse to enter path following.
FEEDBACK_TOPICS = ["FSM/path_planning", "FSM/mode", "driver", "ego_state"]

DEFAULT_SAMPLES = 100
DEFAULT_RUN_TIMEOUT_S = 60.0

# Test knobs. Keep the points in world-frame coordinates.
TEST_START_POINT = (0.0, 0.0)
TEST_END_POINT = (0.2, 0.2)
TEST_VIRTUAL_FORCE_N = 10.0

# Test values from the requirement (ID 13).
BASELINE_TORSIONAL_STIFFNESS = 50.0
HIGH_TORSIONAL_STIFFNESS = 50.0
MAX_ALLOWED_OFFSET_M = 2.0

# "Did the walker actually follow the path" guards. A stationary walker sits
# at (0, 0), which is ON the commanded path (offset = 0), so the 2 m check
# alone is not sufficient evidence.
MIN_FINAL_DISTANCE_M = 0.5
MIN_PROGRESS_RATIO = 0.8
HIGH_STIFFNESS_MARGIN_M = 0.05

# Informational only: we record but do not gate on final heading, since the
# requirement specifies zero heading on the COMMANDED path, not the walker.
FINAL_HEADING_REPORT_RAD = 0.3

IMPEDANCE_PARAMS = {
    "M_v": 5.0,
    "M_w": 2.0,
    "K_v": 0.0,
    "C_v": 15.0,
    # NOTE: the spec writes C_w in "N m s/m", which is dimensionally
    # inconsistent for a torsional damper (expected: N m s/rad). The numeric
    # value is passed through to FSM verbatim; flag this to the spec author.
    "C_w": 15.0,
}

VIRTUAL_COMMAND = {
    "virtual_force": TEST_VIRTUAL_FORCE_N,
    "virtual_torque": 0.0,
}

DELTA_THETA = {
    "difference_function": "atan",
    "reference_function": "look_ahead",
}


def normalized_curvature(u: float, amplitude: float) -> float:
    """Piecewise-linear curvature profile for four joined clothoid segments."""
    # A clothoid has linearly changing curvature. To start and end with zero
    # curvature while still reaching (4,4), we join four clothoid-like segments:
    # 0 -> +k -> 0 -> -k -> 0.
    if u < 0.25:
        return amplitude * (4.0 * u)
    if u < 0.75:
        return amplitude * (2.0 - 4.0 * u)
    return amplitude * (-4.0 + 4.0 * u)


def integrate_normalized_path(
    amplitude: float,
    steps: int = 20000,
) -> tuple[list[float], list[float], list[float]]:
    # Integrate curvature into heading, then heading into x/y.
    # This creates a normalized path first; later we scale it to end at (4,4).
    x_values = [0.0]
    y_values = [0.0]
    theta_values = [0.0]

    x = 0.0
    y = 0.0
    theta = 0.0
    du = 1.0 / steps

    for index in range(steps):
        um = (index + 0.5) * du
        curvature_mid = normalized_curvature(um, amplitude)
        theta_mid = theta + 0.5 * curvature_mid * du

        x += math.cos(theta_mid) * du
        y += math.sin(theta_mid) * du
        theta += curvature_mid * du

        x_values.append(x)
        y_values.append(y)
        theta_values.append(theta)

    theta_values[0] = 0.0
    theta_values[-1] = 0.0
    return x_values, y_values, theta_values


def endpoint_ratio(amplitude: float) -> float:
    x_values, y_values, _ = integrate_normalized_path(amplitude, steps=6000)
    return y_values[-1] / x_values[-1]


def solve_amplitude_for_diagonal() -> float:
    # Find the curvature amplitude that makes the normalized path end with
    # y/x = 1. After scaling, that gives the requested final point (4,4).
    #
    # Bisection assumes endpoint_ratio(amplitude) is monotonically increasing
    # on [0, 12]. This holds because at amplitude=0 the path is straight along
    # +x (ratio = 0) and the four-segment S-curve bends the endpoint smoothly
    # upward as amplitude grows, until self-intersection at much larger values.
    low = 0.0
    high = 12.0
    for _ in range(60):
        mid = 0.5 * (low + high)
        if endpoint_ratio(mid) < 1.0:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def interpolate(values: list[float], ratio: float) -> float:
    if ratio <= 0.0:
        return values[0]
    if ratio >= 1.0:
        return values[-1]
    position = ratio * (len(values) - 1)
    left = int(math.floor(position))
    right = min(left + 1, len(values) - 1)
    alpha = position - left
    return values[left] * (1.0 - alpha) + values[right] * alpha


def generate_clothoid_samples(samples: int) -> tuple[list[float], list[float], list[float]]:
    if samples < 2:
        raise ValueError("samples must be at least 2")

    amplitude = solve_amplitude_for_diagonal()
    x_norm, y_norm, theta_norm = integrate_normalized_path(amplitude)
    scale = 4.0 / x_norm[-1]

    x = []
    y = []
    theta = []
    for index in range(samples):
        ratio = index / (samples - 1)
        x.append(interpolate(x_norm, ratio) * scale)
        y.append(interpolate(y_norm, ratio) * scale)
        theta.append(interpolate(theta_norm, ratio))

    x[0], y[0], theta[0] = 0.0, 0.0, 0.0
    x[-1], y[-1], theta[-1] = 4.0, 4.0, 0.0
    return x, y, theta


def build_payload(samples: int, torsional_stiffness: float) -> dict:
    # This payload shape is what FSM/src/monolithic.cpp expects on topic "GUI":
    # change_mode, path, impedance_params, virtual, and delta_theta are all
    # top-level keys, not wrapped inside another object.
    x, y, theta = generate_clothoid_samples(samples)
    return {
        "change_mode": "path_following_mode",
        "path": {
            "x": x,
            "y": y,
            "theta": theta,
            "inverse_mode": False,
        },
        "impedance_params": {**IMPEDANCE_PARAMS, "K_w": torsional_stiffness},
        "virtual": VIRTUAL_COMMAND,
        "delta_theta": DELTA_THETA,
    }


def cumulative_lengths(path_x: list[float], path_y: list[float]) -> list[float]:
    """Return cumulative arc length at each commanded path sample."""
    lengths = [0.0]
    total = 0.0
    for index in range(1, len(path_x)):
        total += math.hypot(path_x[index] - path_x[index - 1], path_y[index] - path_y[index - 1])
        lengths.append(total)
    return lengths


def project_to_path(
    px: float,
    py: float,
    path_x: list[float],
    path_y: list[float],
    cum_lengths: list[float],
) -> tuple[float, float]:
    """Find the closest point on the path; return (offset, arc_length_at_projection)."""
    best_dist = float("inf")
    best_arc = 0.0
    for index in range(len(path_x) - 1):
        ax, ay = path_x[index], path_y[index]
        bx, by = path_x[index + 1], path_y[index + 1]
        abx = bx - ax
        aby = by - ay
        apx = px - ax
        apy = py - ay
        denom = abx * abx + aby * aby
        if denom == 0.0:
            ratio = 0.0
        else:
            ratio = max(0.0, min(1.0, (apx * abx + apy * aby) / denom))
        cx = ax + ratio * abx
        cy = ay + ratio * aby
        dist = math.hypot(px - cx, py - cy)
        if dist < best_dist:
            best_dist = dist
            seg_len = math.hypot(abx, aby)
            best_arc = cum_lengths[index] + ratio * seg_len
    return best_dist, best_arc


def add_mads_python_path() -> None:
    prefix = subprocess.check_output(["mads", "-p"], text=True).strip()
    python_path = os.path.join(prefix, "python")
    if python_path not in sys.path:
        sys.path.append(python_path)


def configure_agent(agent: object, agent_id: str, key_dir: str) -> None:
    # Same security setup used by test_impedance_control.py.
    agent.set_id(agent_id)
    agent.set_key_dir(key_dir)
    agent.set_client_key_name("broker")
    agent.set_server_key_name("broker")
    agent.set_settings_timeout(2000)


def create_agent(agent_id: str, key_dir: str) -> tuple[object, object]:
    add_mads_python_path()
    from mads_agent import Agent, MessageType

    agent = Agent("path_following_requirement_test")
    configure_agent(agent, agent_id=agent_id, key_dir=key_dir)

    # Publish path commands to GUI and listen to FSM feedback for evidence.
    agent.set_pub_topic(GUI_TOPIC)
    agent.set_sub_topics(FEEDBACK_TOPICS)

    while agent.init(True) != 0:
        print("Cannot contact MADS broker. Retrying...")
        time.sleep(1.0)

    if agent.set_queue_size(200) != 0:
        raise RuntimeError(f"MADS queue setup failed: {agent.last_error()}")

    result = agent.connect()
    if result != 0:
        raise RuntimeError(f"MADS connect failed: {agent.last_error()}")

    agent.set_receive_timeout(100)
    return agent, MessageType


def publish(agent: object, payload: dict) -> None:
    result = agent.publish(payload, topic=GUI_TOPIC)
    if result != 0:
        raise RuntimeError(f"MADS publish failed: {agent.last_error()}")


def drain_messages(
    agent: object,
    message_type: object,
    max_messages: int = 200,
    max_seconds: float = 0.25,
) -> None:
    # ego_state can arrive continuously; drain briefly, then let the run loop
    # handle fresh feedback.
    deadline = time.time() + max_seconds
    for _ in range(max_messages):
        if time.time() >= deadline or agent.receive() == message_type.NONE:
            break


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize_run(
    label: str,
    stiffness: float,
    poses: list[dict],
    mode_history: list[dict],
    completion_reason: str,
    path_total_length: float,
) -> dict:
    offsets = [pose["offset"] for pose in poses]
    max_offset = max(offsets) if offsets else None

    # Did the walker actually traverse the path?
    if poses:
        final_pose = poses[-1]
        final_distance_to_goal = math.hypot(final_pose["x"] - 4.0, final_pose["y"] - 4.0)
        final_theta = final_pose["theta"]
        max_arc_reached = max(pose["arc_length"] for pose in poses)
        progress_ratio = max_arc_reached / path_total_length if path_total_length > 0 else 0.0
    else:
        final_distance_to_goal = None
        final_theta = None
        max_arc_reached = 0.0
        progress_ratio = 0.0

    completed = completion_reason in ("fsm_mode_transition", "quiet_after_active")
    within_offset = bool(offsets) and max_offset <= MAX_ALLOWED_OFFSET_M
    reached_goal = (
        final_distance_to_goal is not None
        and final_distance_to_goal <= MIN_FINAL_DISTANCE_M
    )
    covered_path = progress_ratio >= MIN_PROGRESS_RATIO
    walker_actually_moved = reached_goal and covered_path

    return {
        "label": label,
        "torsional_stiffness_K_w": stiffness,
        "samples_recorded": len(poses),
        "completed": completed,
        "completion_reason": completion_reason,
        "max_offset_m": max_offset,
        "mean_offset_m": mean(offsets),
        "final_distance_to_goal_m": final_distance_to_goal,
        "final_theta_rad": final_theta,
        "progress_ratio": progress_ratio,
        "max_arc_reached_m": max_arc_reached,
        "path_total_length_m": path_total_length,
        "passed_offset_requirement": within_offset,
        "walker_actually_moved": walker_actually_moved,
        "reached_goal": reached_goal,
        "covered_path": covered_path,
        "mode_history": mode_history,
        "poses": poses,
    }


def run_single_test(
    agent: object,
    message_type: object,
    label: str,
    stiffness: float,
    samples: int,
    timeout_s: float,
    quiet_after_active_s: float,
) -> dict:
    # One run means: reset to idle, send path-following mode and parameters,
    # then record walker poses until FSM finishes, becomes quiet, or times out.
    path_x, path_y, _ = generate_clothoid_samples(samples)
    cum_lengths = cumulative_lengths(path_x, path_y)
    path_total_length = cum_lengths[-1]
    payload = build_payload(samples=samples, torsional_stiffness=stiffness)

    print(f"\n{label}: setting idle")
    publish(agent, {"change_mode": "idle"})
    time.sleep(1.0)
    drain_messages(agent, message_type)

    print(f"{label}: sending path_following_mode with K_w={stiffness:g}")
    publish(agent, {"change_mode": "path_following_mode"})
    time.sleep(0.5)
    publish(agent, payload)

    poses: list[dict] = []
    mode_history: list[dict] = []
    start = time.time()
    last_path_message = start
    last_status = start
    last_mode = "unknown"
    last_driver_state = "unknown"
    ego_state_seen = False
    active_seen = False
    completion_reason = "hard_timeout"

    while time.time() - start < timeout_s:
        if agent.receive() == message_type.NONE:
            if time.time() - last_status >= 2.0 and not active_seen:
                ego_status = "seen" if ego_state_seen else "not seen"
                print(
                    f"{label}: waiting for path following "
                    f"(mode={last_mode}, driver={last_driver_state}, ego_state={ego_status})"
                )
                last_status = time.time()
            if active_seen and time.time() - last_path_message >= quiet_after_active_s:
                completion_reason = "quiet_after_active"
                break
            continue

        topic, message = agent.last_message()
        elapsed = time.time() - start

        if topic == "FSM/mode" and isinstance(message, dict) and "mode" in message:
            # FSM confirms transitions such as path_following_active here.
            mode = message["mode"]
            last_mode = str(mode)
            print(f"{label}: FSM mode -> {mode}")
            mode_history.append({"t_s": elapsed, "mode": mode})
            if mode == "path_following_active":
                active_seen = True
            elif active_seen:
                completion_reason = "fsm_mode_transition"
                break

        if topic == "driver" and isinstance(message, dict):
            driver_state = "blocked/warning" if "warning" in message else "clear"
            if driver_state != last_driver_state:
                last_driver_state = driver_state
                print(f"{label}: driver state -> {driver_state}")
            if driver_state == "blocked/warning" and not active_seen:
                completion_reason = "driver_blocked_before_path_following_active"
                print(f"{label}: driver is blocking the FSM transition; stopping this run")
                break
            continue

        if topic == "ego_state":
            if not ego_state_seen:
                ego_state_seen = True
                print(f"{label}: ego_state feedback received")
            continue

        if topic != "FSM/path_planning" or not isinstance(message, dict):
            continue

        walker_pose = message.get("walker_pose")
        if not isinstance(walker_pose, list) or len(walker_pose) < 2:
            continue

        # FSM/path_planning gives the current walker pose. We compare it with
        # the standard clothoid path by computing the nearest path distance
        # and the arc length at the nearest point (used for progress).
        active_seen = True
        if len(poses) == 0:
            print(f"{label}: first FSM/path_planning sample received")
        last_path_message = time.time()
        x = float(walker_pose[0])
        y = float(walker_pose[1])
        theta = float(walker_pose[2]) if len(walker_pose) > 2 else 0.0
        reference = message.get("reference", [])
        offset, arc_length = project_to_path(x, y, path_x, path_y, cum_lengths)

        poses.append(
            {
                "t_s": elapsed,
                "x": x,
                "y": y,
                "theta": theta,
                "reference": reference,
                "offset": offset,
                "arc_length": arc_length,
            }
        )

    result = summarize_run(
        label=label,
        stiffness=stiffness,
        poses=poses,
        mode_history=mode_history,
        completion_reason=completion_reason,
        path_total_length=path_total_length,
    )

    publish(agent, {"change_mode": "idle"})
    time.sleep(1.0)
    return result


def build_report(baseline: dict, high_stiffness: dict) -> dict:
    # Acceptance combines all four guards described in the module docstring.
    baseline_max = baseline["max_offset_m"]
    high_max = high_stiffness["max_offset_m"]
    improvement = None
    improved_with_margin = False
    if baseline_max is not None and high_max is not None:
        improvement = baseline_max - high_max
        improved_with_margin = improvement >= HIGH_STIFFNESS_MARGIN_M

    each_run_valid = (
        baseline["passed_offset_requirement"]
        and baseline["walker_actually_moved"]
        and baseline["completed"]
        and high_stiffness["passed_offset_requirement"]
        and high_stiffness["walker_actually_moved"]
        and high_stiffness["completed"]
    )

    passed = each_run_valid and improved_with_margin

    return {
        "passed": passed,
        "requirements": {
            "topic": GUI_TOPIC,
            "path": "joined clothoid from (0,0) to (4,4), zero heading and curvature at both ends",
            "max_allowed_offset_m": MAX_ALLOWED_OFFSET_M,
            "min_final_distance_m": MIN_FINAL_DISTANCE_M,
            "min_progress_ratio": MIN_PROGRESS_RATIO,
            "high_stiffness_margin_m": HIGH_STIFFNESS_MARGIN_M,
            "baseline_K_w": BASELINE_TORSIONAL_STIFFNESS,
            "high_K_w": HIGH_TORSIONAL_STIFFNESS,
            "impedance_params": {
                **IMPEDANCE_PARAMS,
                "K_w": BASELINE_TORSIONAL_STIFFNESS,
            },
            "virtual": VIRTUAL_COMMAND,
            "delta_theta": DELTA_THETA,
        },
        "baseline": baseline,
        "high_stiffness": high_stiffness,
        "high_stiffness_improved": improved_with_margin,
        "max_offset_improvement_m": improvement,
    }


def show_terminal_plots(report: dict, samples: int) -> None:
    try:
        import plotext as plt
    except ImportError:
        print("\nplotext is not installed, so terminal plots were skipped.")
        return

    path_x, path_y, _ = generate_clothoid_samples(samples)
    baseline_poses = report["baseline"]["poses"]
    high_poses = report["high_stiffness"]["poses"]

    # First plot: path geometry and the recorded walker trajectories.
    plt.clf()
    plt.title("Path Following Trajectory")
    plt.xlabel("x [m]")
    plt.ylabel("y [m]")
    plt.plot(path_x, path_y, label="standard clothoid path")
    if baseline_poses:
        plt.plot(
            [pose["x"] for pose in baseline_poses],
            [pose["y"] for pose in baseline_poses],
            label="baseline K_w=25",
        )
    if high_poses:
        plt.plot(
            [pose["x"] for pose in high_poses],
            [pose["y"] for pose in high_poses],
            label="high stiffness K_w=50",
        )
    plt.show()

    # Second plot: distance from the standard path during each run.
    plt.clf()
    plt.title("Offset From Standard Path")
    plt.xlabel("sample")
    plt.ylabel("offset [m]")
    if baseline_poses:
        plt.plot(
            list(range(1, len(baseline_poses) + 1)),
            [pose["offset"] for pose in baseline_poses],
            label="baseline K_w=25",
        )
    if high_poses:
        plt.plot(
            list(range(1, len(high_poses) + 1)),
            [pose["offset"] for pose in high_poses],
            label="high stiffness K_w=50",
        )
    longest = max(len(baseline_poses), len(high_poses), 1)
    plt.plot(
        list(range(1, longest + 1)),
        [MAX_ALLOWED_OFFSET_M] * longest,
        label="2 m limit",
    )
    plt.show()


def _format_optional(value: float | None, fmt: str = "{:.3f}") -> str:
    return "n/a" if value is None else fmt.format(value)


def _print_run_summary(run: dict) -> None:
    print(f"  label:                {run['label']}")
    print(f"  K_w:                  {run['torsional_stiffness_K_w']}")
    print(f"  samples recorded:     {run['samples_recorded']}")
    print(f"  completion reason:    {run['completion_reason']} (completed={run['completed']})")
    print(f"  max offset [m]:       {_format_optional(run['max_offset_m'])}")
    print(f"  mean offset [m]:      {_format_optional(run['mean_offset_m'])}")
    print(f"  final dist to goal:   {_format_optional(run['final_distance_to_goal_m'])} m")
    print(
        f"  final heading:        {_format_optional(run['final_theta_rad'])} rad"
        + (
            " (>tol, informational)"
            if run["final_theta_rad"] is not None
            and abs(run["final_theta_rad"]) > FINAL_HEADING_REPORT_RAD
            else ""
        )
    )
    print(
        f"  progress ratio:       {run['progress_ratio']:.3f} "
        f"({run['max_arc_reached_m']:.3f} / {run['path_total_length_m']:.3f} m)"
    )
    print(f"  within 2 m offset:    {run['passed_offset_requirement']}")
    print(f"  reached goal:         {run['reached_goal']}")
    print(f"  covered path:         {run['covered_path']}")
    print(f"  walker actually moved:{run['walker_actually_moved']}")


def print_summary(report: dict) -> None:
    print("\nRESULT")
    print(f"passed: {report['passed']}")
    print("\nBaseline run:")
    _print_run_summary(report["baseline"])
    print("\nHigh-stiffness run:")
    _print_run_summary(report["high_stiffness"])

    improvement = report["max_offset_improvement_m"]
    print(
        "\nhigh stiffness offset improvement: "
        f"{_format_optional(improvement)} m "
        f"(required >= {HIGH_STIFFNESS_MARGIN_M} m, "
        f"got {report['high_stiffness_improved']})"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--timeout", type=float, default=DEFAULT_RUN_TIMEOUT_S)
    parser.add_argument("--quiet-after-active", type=float, default=3.0)
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument(
        "--key-dir",
        default=os.environ.get("MADS_KEY_DIR", "/home/miro/security"),
        help="Path to the MADS key directory (default: /home/miro/security or $MADS_KEY_DIR)",
    )
    parser.add_argument(
        "--agent-id",
        default=os.environ.get("MADS_AGENT_ID", "python"),
        help="MADS agent ID (default: python or $MADS_AGENT_ID)",
    )
    args = parser.parse_args()

    agent, message_type = create_agent(agent_id=args.agent_id, key_dir=args.key_dir)
    try:
        baseline = run_single_test(
            agent=agent,
            message_type=message_type,
            label="baseline",
            stiffness=BASELINE_TORSIONAL_STIFFNESS,
            samples=args.samples,
            timeout_s=args.timeout,
            quiet_after_active_s=args.quiet_after_active,
        )
        high_stiffness = None
        if baseline["completion_reason"] == "driver_blocked_before_path_following_active":
            print("\nDriver blocked the baseline run; high-stiffness run skipped.")
        else:
            high_stiffness = run_single_test(
                agent=agent,
                message_type=message_type,
                label="high_stiffness",
                stiffness=HIGH_TORSIONAL_STIFFNESS,
                samples=args.samples,
                timeout_s=args.timeout,
                quiet_after_active_s=args.quiet_after_active,
            )
    finally:
        try:
            publish(agent, {"change_mode": "idle"})
        except Exception as error:
            print(f"Could not send final idle command: {error}")
        agent.destroy()

    if high_stiffness is None:
        print("\nRESULT")
        print("passed: False")
        print("\nBaseline run:")
        _print_run_summary(baseline)
        return 2

    report = build_report(baseline, high_stiffness)
    if not args.no_plots:
        show_terminal_plots(report, args.samples)

    print_summary(report)
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
