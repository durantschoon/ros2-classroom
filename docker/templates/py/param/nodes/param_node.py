"""
A node with a declared, runtime-changeable parameter.

Usage:
ros2 run @PKG@ param_node
ros2 param list
ros2 param set /param_node greeting "good evening"
"""

import rclpy
from rclpy.node import Node


class ParamNode(Node):

    def __init__(self):
        super().__init__('param_node')
        # Declaring a parameter is what makes it visible to `ros2 param`.
        self.declare_parameter('greeting', 'hello')
        self.timer = self.create_timer(1.0, self.on_timer)

    def on_timer(self):
        greeting = self.get_parameter('greeting').get_parameter_value().string_value
        self.get_logger().info(f'{greeting} from @PKG@')


def main(args=None):
    rclpy.init(args=args)
    node = ParamNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
