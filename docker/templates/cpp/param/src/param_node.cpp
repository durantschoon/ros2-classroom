// A node with a declared, runtime-changeable parameter.
//
//   ros2 run @PKG@ param_node
//   ros2 param list
//   ros2 param set /param_node greeting "good evening"
#include <chrono>
#include <string>

#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

class ParamNode : public rclcpp::Node
{
public:
  ParamNode()
  : Node("param_node")
  {
    // Declaring a parameter is what makes it visible to `ros2 param`.
    this->declare_parameter("greeting", "hello");
    timer_ = this->create_wall_timer(1s, std::bind(&ParamNode::on_timer, this));
  }

private:
  void on_timer()
  {
    std::string greeting = this->get_parameter("greeting").as_string();
    RCLCPP_INFO(this->get_logger(), "%s from @PKG@", greeting.c_str());
  }

  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ParamNode>());
  rclcpp::shutdown();
  return 0;
}
