"""
A minimal publisher.

Usage: ros2 run @PKG@ talker
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):

    def __init__(self):
        super().__init__('talker')
        self.publisher = self.create_publisher(String, 'chatter', 10)
        self.timer = self.create_timer(0.5, self.on_timer)
        self.count = 0

    def on_timer(self):
        message = String()
        message.data = f'hello from @PKG@ #{self.count}'
        self.count += 1
        self.publisher.publish(message)
        self.get_logger().info(f"publishing: '{message.data}'")


def main(args=None):
    rclpy.init(args=args)
    node = Talker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
