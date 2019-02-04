from data_providers import *

provider = SSLVisionDataProvider()
provider.start()

print(provider.get_ball_position())
print(provider.get_robot_position(9, team='blue'))

provider.stop()