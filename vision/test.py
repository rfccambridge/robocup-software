from data_providers import SSLVisionDataProvider

provider = SSLVisionDataProvider()
provider.start()

print("ball pos\n", provider._get_ball_position())
print("robot id: 8\n", provider._get_robot_position(8, team='blue'))
print("all robots:\n", provider._get_robot_positions())

provider.stop()