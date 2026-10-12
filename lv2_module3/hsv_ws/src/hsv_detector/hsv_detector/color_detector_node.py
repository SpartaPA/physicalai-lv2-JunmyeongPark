import json
import os
import platform
import sys
import time

import cv2
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped
from rcl_interfaces.msg import (FloatingPointRange, IntegerRange, ParameterDescriptor,
                                SetParametersResult)
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage, Image
from std_msgs.msg import String

from hsv_detector.color_detector import ColorDetector, draw_overlay


def _int_range(lo, hi):
    return ParameterDescriptor(integer_range=[IntegerRange(from_value=lo, to_value=hi, step=1)])


def _float_range(lo, hi, step=0.0):
    return ParameterDescriptor(floating_point_range=[FloatingPointRange(from_value=lo, to_value=hi, step=step)])


TUNABLE = {
    'h_lo': (100, _int_range(0, 179)), 'h_hi': (125, _int_range(0, 179)),
    's_lo': (120, _int_range(0, 255)), 's_hi': (255, _int_range(0, 255)),
    'v_lo': (40, _int_range(0, 255)), 'v_hi': (255, _int_range(0, 255)),
    'min_area': (300.0, _float_range(0.0, 20000.0)),
    'min_circularity': (0.3, _float_range(0.0, 1.0)),
    'ema_alpha': (0.3, _float_range(0.0, 1.0)),
    'blur_ksize': (5, _int_range(1, 31)),
    'morph_ksize': (5, _int_range(0, 31)),
}


class ColorDetectorNode(Node):
    def __init__(self):
        super().__init__('color_detector')
        p = self.declare_parameter
        p('image_topic', '/image_raw')
        p('input_compressed', False)
        p('reliable_input', False)
        p('publish_input', True)
        p('publish_compressed', True)
        for name, (default, desc) in TUNABLE.items():
            p(name, default, desc)
        p('hsv_lo2', [-1, -1, -1])
        p('hsv_hi2', [-1, -1, -1])
        p('label', '')

        g = lambda n: self.get_parameter(n).value
        lo2, hi2 = list(g('hsv_lo2')), list(g('hsv_hi2'))
        self.cfg = {
            'lo2': lo2 if min(lo2) >= 0 else None,
            'hi2': hi2 if min(hi2) >= 0 else None,
        }
        self._apply({n: g(n) for n in TUNABLE})
        self.label = g('label')
        self.publish_input = bool(g('publish_input'))
        self.det = ColorDetector(self.cfg)
        self.add_on_set_parameters_callback(self.on_params)
        self.bridge = CvBridge()
        self.seq = 0

        if g('reliable_input'):
            qos_in = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE,
                                history=HistoryPolicy.KEEP_LAST)
        else:
            qos_in = qos_profile_sensor_data
        topic = g('image_topic')
        if g('input_compressed'):
            self.sub = self.create_subscription(CompressedImage, topic, self.on_compressed, qos_in)
        else:
            self.sub = self.create_subscription(Image, topic, self.on_image, qos_in)

        qos_img = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT,
                             history=HistoryPolicy.KEEP_LAST)
        self.pub_in = self.create_publisher(Image, 'image_input', qos_img)
        self.pub_mask = self.create_publisher(Image, 'mask', qos_img)
        self.pub_dbg = self.create_publisher(Image, 'image_annotated', qos_img)
        self.publish_compressed = bool(g('publish_compressed'))
        self.pub_in_c = self.create_publisher(CompressedImage, 'image_input/compressed', qos_img)
        self.pub_dbg_c = self.create_publisher(CompressedImage, 'image_annotated/compressed', qos_img)
        self.pub_pt = self.create_publisher(PointStamped, 'detection', 10)
        self.pub_stats = self.create_publisher(String, 'detection_stats', 10)

        self.get_logger().info(
            f"python {platform.python_version()} | opencv {cv2.__version__} | "
            f"ROS_DISTRO={os.environ.get('ROS_DISTRO', '?')} | label={self.label!r}")
        self.get_logger().info(f"input {topic} (compressed={g('input_compressed')}) cfg={json.dumps(self.cfg)}")

        self._win_n, self._win_cb, self._win_det = 0, 0.0, 0.0
        self.create_timer(5.0, self._report_rate)

    def _report_rate(self):
        n = self._win_n
        if n:
            self.get_logger().info(f"처리 {n}프레임/5s = {n / 5:.1f} Hz | 콜백 평균 {self._win_cb / n * 1e3:.1f} ms "
                                   f"(검출 {self._win_det / n * 1e3:.1f} ms)")
        else:
            self.get_logger().info('5 s 동안 입력 프레임 없음')
        self._win_n, self._win_cb, self._win_det = 0, 0.0, 0.0

    def _apply(self, vals):
        cur = {n: self.get_parameter(n).value for n in TUNABLE}
        cur.update(vals)
        self.cfg.update({
            'lo': [int(cur['h_lo']), int(cur['s_lo']), int(cur['v_lo'])],
            'hi': [int(cur['h_hi']), int(cur['s_hi']), int(cur['v_hi'])],
            'min_area': float(cur['min_area']),
            'min_circularity': float(cur['min_circularity']),
            'ema_alpha': float(cur['ema_alpha']),
            'blur_ksize': int(cur['blur_ksize']) | 1,
            'morph_ksize': int(cur['morph_ksize']),
        })

    def on_params(self, params):
        vals = {prm.name: prm.value for prm in params if prm.name in TUNABLE}
        if vals:
            self._apply(vals)
            self.get_logger().info(f"param 변경 {vals} -> lo={self.cfg['lo']} hi={self.cfg['hi']} "
                                   f"min_area={self.cfg['min_area']} min_circ={self.cfg['min_circularity']}")
        return SetParametersResult(successful=True)

    def on_image(self, msg):
        t0 = time.perf_counter()
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self.process(frame, msg.header)
        self._win_cb += time.perf_counter() - t0

    def on_compressed(self, msg):
        t0 = time.perf_counter()
        frame = self.bridge.compressed_imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self.process(frame, msg.header)
        self._win_cb += time.perf_counter() - t0

    def process(self, frame, header):
        self.seq += 1
        self._win_n += 1
        r, mask, stats = self.det.step(frame)
        self._win_det += (stats['t_mask_ms'] + stats['t_detect_ms']) / 1e3

        if self.publish_input:
            m = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
            m.header = header
            self.pub_in.publish(m)
            if self.publish_compressed:
                c = self.bridge.cv2_to_compressed_imgmsg(frame, 'jpg')
                c.header = header
                self.pub_in_c.publish(c)
        mm = self.bridge.cv2_to_imgmsg(mask, 'mono8')
        mm.header = header
        self.pub_mask.publish(mm)
        overlay = draw_overlay(frame, r)
        dm = self.bridge.cv2_to_imgmsg(overlay, 'bgr8')
        dm.header = header
        self.pub_dbg.publish(dm)
        if self.publish_compressed:
            c = self.bridge.cv2_to_compressed_imgmsg(overlay, 'jpg')
            c.header = header
            self.pub_dbg_c.publish(c)

        out = {
            'label': self.label,
            'seq': self.seq,
            'stamp': header.stamp.sec + header.stamp.nanosec * 1e-9,
            'detected': r is not None,
            'mask_pixels': int(cv2.countNonZero(mask)),
            **stats,
        }
        if r is not None:
            pt = PointStamped()
            pt.header = header
            pt.point.x, pt.point.y, pt.point.z = float(r['cx']), float(r['cy']), float(r['area'])
            self.pub_pt.publish(pt)
            out.update({
                'cx_raw': r['center'][0], 'cy_raw': r['center'][1],
                'cx': r['cx'], 'cy': r['cy'],
                'area': r['area'], 'circularity': r['circularity'],
                'bbox': list(r['bbox']),
            })
        self.pub_stats.publish(String(data=json.dumps(out)))


def main(args=None):
    rclpy.init(args=args)
    node = ColorDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
