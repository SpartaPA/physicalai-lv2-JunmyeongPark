import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _cfg_path(name):
    if os.path.isabs(name):
        return name
    return os.path.join(get_package_share_directory('hsv_detector'), 'config', name)


def _setup(context):
    lc = lambda n: LaunchConfiguration(n).perform(context)
    common = {
        'image_topic': lc('image_topic'),
        'input_compressed': lc('input_compressed').lower() == 'true',
        'reliable_input': lc('reliable_input').lower() == 'true',
    }
    cfg_b = lc('config_b')
    nodes = []
    if cfg_b:
        for ns, cfg in (('A', lc('config')), ('B', cfg_b)):
            nodes.append(Node(package='hsv_detector', executable='color_detector_node',
                              name='color_detector', namespace=ns, output='screen',
                              parameters=[_cfg_path(cfg), common]))
    else:
        nodes.append(Node(package='hsv_detector', executable='color_detector_node',
                          name='color_detector', namespace=lc('ns'), output='screen',
                          parameters=[_cfg_path(lc('config')), common]))
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('config', default_value='base.yaml'),
        DeclareLaunchArgument('config_b', default_value='',
                              description='지정하면 config 를 /A, config_b 를 /B 로 동시에 실행'),
        DeclareLaunchArgument('ns', default_value='hsv', description='단일 실행 시 namespace'),
        DeclareLaunchArgument('image_topic', default_value='/camera/camera/color/image_raw'),
        DeclareLaunchArgument('input_compressed', default_value='false'),
        DeclareLaunchArgument('reliable_input', default_value='true',
                              description='bag 재생 시 true 권장 (A/B가 같은 프레임을 모두 받도록)'),
        OpaqueFunction(function=_setup),
    ])
