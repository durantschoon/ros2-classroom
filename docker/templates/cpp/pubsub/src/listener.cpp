// A minimal subscriber.  Run it with:  ros2 run @PKG@ listener
#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

using std::placeholders::_1;

class Listener : public rclcpp::Node
{
public:
  Listener()
  : Node("listener")
  {
    subscription_ = this->create_subscription<std_msgs::msg::String>(
      "chatter", 10, std::bind(&Listener::on_message, this, _1));
  }

private:
  void on_message(const std_msgs::msg::String & msg) const
  {
    RCLCPP_INFO(this->get_logger(), "heard: '%s'", msg.data.c_str());
  }

  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Listener>());
  rclcpp::shutdown();
  return 0;
}
