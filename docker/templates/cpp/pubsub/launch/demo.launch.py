"""
Start the talker and listener together.

Usage: ros2 launch @PKG@ demo.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='@PKG@',
            executable='talker',
            name='talker',
            output='screen',
        ),
        Node(
            package='@PKG@',
            executable='listener',
            name='listener',
            output='screen',
        ),
    ])
