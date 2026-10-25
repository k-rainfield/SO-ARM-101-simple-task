
This ROS 2 Jazzy package starts `lerobot-rollout` as a managed subprocess and
loads the local ACT policy from `checkpoints/last/pretrained_model`.

## Requirements

- Pixi
- ROS 2 Jazzy and a working LeRobot installation in the Pixi environment
- A calibrated SO-ARM-101 follower, its serial port, and a camera visible to OpenCV

## Build and run

From the repository root:

```bash
pixi install
pixi run build
pixi run rollout --ros-args -p robot_port:=/dev/ttyACM0 -p robot_id:=so_arm101_follower -p camera_index:=0
```

The rollout runs for 30 seconds by default. Override `duration`, camera
resolution/FPS, policy path, or the robot settings with ROS parameters. For
example, use `-p duration:=60.0 -p camera_index:=/dev/video2`. Additional
LeRobot options can be supplied as a shell-style string in the `extra_args` parameter.
Set `policy_device` to `cuda` or `cpu` to override the device recorded in the
policy configuration; by default, LeRobot uses the policy's configured device.

The node exits when the rollout finishes. Pressing Ctrl-C stops the
`lerobot-rollout` process group as well.