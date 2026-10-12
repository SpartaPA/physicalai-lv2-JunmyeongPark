from glob import glob
from setuptools import setup

package_name = 'hsv_detector'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='JunmyeongPark',
    maintainer_email='cvlab7079@gmail.com',
    description='HSV mask + contour color detector node',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'color_detector_node = hsv_detector.color_detector_node:main',
            'bag_tools = hsv_detector.bag_tools:main',
        ],
    },
)
