"""
A minimal subscriber.

Usage: ros2 run @PKG@ listener
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Listener(Node):

    def __init__(self):
        super().__init__('listener')
        self.subscription = self.create_subscription(
            String, 'chatter', self.on_message, 10)

    def on_message(self, msg):
        self.get_logger().info(f"heard: '{msg.data}'")


def main(args=None):
    rclpy.init(args=args)
    node = Listener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
