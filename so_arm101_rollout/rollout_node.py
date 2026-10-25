import json
import os
import shlex
import shutil
import signal
import subprocess
from pathlib import Path

import rclpy
from rclpy.node import Node


class RolloutNode(Node):
    def __init__(self):
        super().__init__("so_arm101_rollout")
        self.declare_parameter("policy_path", os.environ.get("SO_ARM101_POLICY_PATH", "checkpoints/last/pretrained_model"))
        self.declare_parameter("robot_type", "so101_follower")
        self.declare_parameter("robot_port", "/dev/ttyACM0")
        self.declare_parameter("robot_id", "so_arm101_follower")
        self.declare_parameter("camera_index", "0")
        self.declare_parameter("camera_width", 640)
        self.declare_parameter("camera_height", 480)
        self.declare_parameter("camera_fps", 30)
        self.declare_parameter("task", "SO-ARM-101 ACT rollout")
        self.declare_parameter("duration", 30.0)
        self.declare_parameter("policy_device", "")
        self.declare_parameter("lerobot_command", "lerobot-rollout")
        self.declare_parameter("extra_args", "")

        self.process = None
        self.return_code = None
        self._start_rollout()
        self.create_timer(0.5, self._check_process)

    def _start_rollout(self):
        policy_path = Path(self.get_parameter("policy_path").value).expanduser()
        if not policy_path.is_absolute():
            policy_path = Path.cwd() / policy_path
        if not (policy_path / "config.json").is_file():
            raise FileNotFoundError(f"ACT policy config not found: {policy_path / 'config.json'}")

        command = self.get_parameter("lerobot_command").value
        executable = shutil.which(command)
        if executable is None:
            raise FileNotFoundError(f"Cannot find {command!r}; run this node inside the pixi environment")

        camera_index = self.get_parameter("camera_index").value
        if camera_index.isdecimal():
            camera_index = int(camera_index)
        camera_config = {
            "front": {
                "type": "opencv",
                "index_or_path": camera_index,
                "width": self.get_parameter("camera_width").value,
                "height": self.get_parameter("camera_height").value,
                "fps": self.get_parameter("camera_fps").value,
            }
        }
        arguments = [
            executable,
            "--strategy.type=base",
            f"--policy.path={policy_path}",
            f"--robot.type={self.get_parameter('robot_type').value}",
            f"--robot.port={self.get_parameter('robot_port').value}",
            f"--robot.id={self.get_parameter('robot_id').value}",
            f"--robot.cameras={json.dumps(camera_config)}",
            f"--task={self.get_parameter('task').value}",
            f"--duration={self.get_parameter('duration').value}",
        ]
        policy_device = self.get_parameter("policy_device").value
        if policy_device:
            arguments.append(f"--policy.device={policy_device}")
        arguments.extend(shlex.split(self.get_parameter("extra_args").value))

        self.get_logger().info("Starting LeRobot rollout: " + " ".join(arguments))
        self.process = subprocess.Popen(arguments, start_new_session=True)

    def _check_process(self):
        if self.process is None:
            return
        return_code = self.process.poll()
        if return_code is not None:
            self.return_code = return_code
            log = self.get_logger().info if return_code == 0 else self.get_logger().error
            log(f"lerobot-rollout exited with status {return_code}")
            rclpy.shutdown()

    def stop_rollout(self):
        if self.process is None or self.process.poll() is not None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGINT)
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait()


def main(args=None):
    rclpy.init(args=args)
    node = None
    exit_code = 1
    try:
        node = RolloutNode()
        rclpy.spin(node)
        exit_code = node.return_code if node.return_code is not None else 0
    except (FileNotFoundError, OSError, ValueError) as error:
        if node is not None:
            node.get_logger().error(str(error))
        else:
            print(f"Failed to start SO-ARM-101 rollout: {error}", flush=True)
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        if node is not None:
            node.stop_rollout()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()