import argparse
import json
import os
from collections import defaultdict

import cv2
import numpy as np
import rosbag2_py
from cv_bridge import CvBridge
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


def _read(uri, want):
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=uri, storage_id=''),
                rosbag2_py.ConverterOptions('cdr', 'cdr'))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    msg_cls = {}
    while reader.has_next():
        topic, data, _ = reader.read_next()
        if not want(topic):
            continue
        if topic not in msg_cls:
            msg_cls[topic] = get_message(types[topic])
        yield topic, deserialize_message(data, msg_cls[topic])


def _stats(bag):
    out = defaultdict(dict)
    for topic, msg in _read(bag, lambda t: t.endswith('/detection_stats')):
        d = json.loads(msg.data)
        out[topic.rsplit('/', 1)[0]][round(d['stamp'], 3)] = d
    return dict(sorted(out.items()))


def summary(args):
    S = _stats(args.bag)
    if not S:
        print('detection_stats 토픽이 없습니다.')
        return
    t_first = min(st for v in S.values() for st in v)
    keep = lambda st: ((args.t0 is None or st - t_first >= args.t0)
                       and (args.t1 is None or st - t_first <= args.t1))
    print(f'기준 시각(첫 입력 프레임 stamp) = {t_first:.3f}')
    print('ns | label | frames | detected | det_rate | mean_contours | mean_pass_area | mean_pass_shape | '
          'mean_mask_px | mean_t_ms | area(min/med/max, 검출 프레임)')
    for ns, v in S.items():
        rs = [r for st, r in sorted(v.items()) if keep(st)]
        if not rs:
            print(f'{ns} | - | 0')
            continue
        n = len(rs)
        k = sum(r['detected'] for r in rs)
        mean = lambda key: sum(r[key] for r in rs) / n
        t_ms = sum(r['t_mask_ms'] + r['t_detect_ms'] for r in rs) / n
        areas = sorted(r['area'] for r in rs if r['detected'])
        area_s = f'{areas[0]:.0f}/{areas[len(areas) // 2]:.0f}/{areas[-1]:.0f}' if areas else '-'
        print(f"{ns} | {rs[0]['label']} | {n} | {k} | {k / n:.3f} | {mean('n_contours'):.2f} | "
              f"{mean('n_pass_area'):.2f} | {mean('n_pass_shape'):.2f} | {mean('mask_pixels'):.0f} | "
              f"{t_ms:.2f} | {area_s}")

    if len(S) == 2:
        (na, A), (nb, B) = S.items()
        common = sorted(st for st in A if st in B and keep(st))
        print(f'\n같은 입력 프레임 확인: {na} {sum(map(keep, A))}개, {nb} {sum(map(keep, B))}개, 공통 stamp {len(common)}개')
        cnt = defaultdict(int)
        diff = []
        for st in common:
            a, b = A[st], B[st]
            if a['detected'] and b['detected']:
                far = abs(a['cx_raw'] - b['cx_raw']) > 30 or abs(a['cy_raw'] - b['cy_raw']) > 30
                cnt['둘 다 검출, 중심 차이 >30px' if far else '둘 다 검출, 같은 대상'] += 1
                if far:
                    diff.append(('다른 대상', st))
            elif a['detected']:
                cnt[f'{na}만 검출'] += 1
                diff.append((f'{na}만', st))
            elif b['detected']:
                cnt[f'{nb}만 검출'] += 1
                diff.append((f'{nb}만', st))
            else:
                cnt['둘 다 미검출'] += 1
        for key, c in cnt.items():
            print(f'  {key}: {c}')
        if diff and len(diff) <= 60:
            print('  갈린 프레임 [s]: ' + ', '.join(f'{kind} {st - t_first:.2f}' for kind, st in diff))
        elif diff:
            print(f'  갈린 프레임 {len(diff)}개 (60개 초과, 생략)')


def _label(img, text):
    img = img.copy() if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(img, (0, 0), (img.shape[1], 26), (0, 0, 0), -1)
    cv2.putText(img, text, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    return img


def export(args):
    if not args.at:
        print('--at 으로 시각을 지정하세요.')
        return
    S = _stats(args.bag)
    if not S:
        print('detection_stats 토픽이 없습니다.')
        return
    t_first = min(st for v in S.values() for st in v)
    ns_list = list(S)
    stamps = sorted(S[ns_list[0]])
    targets = {min(stamps, key=lambda s: abs(s - t_first - t)) for t in args.at}

    bridge = CvBridge()
    want = {f'{ns}/{k}' for ns in ns_list for k in ('mask', 'image_annotated/compressed')}
    want.add(f'{ns_list[0]}/image_input/compressed')
    imgs = defaultdict(dict)
    for topic, m in _read(args.bag, lambda t: t in want):
        st = round(m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, 3)
        if st not in targets:
            continue
        if hasattr(m, 'format'):
            imgs[topic][st] = bridge.compressed_imgmsg_to_cv2(m, 'bgr8')
        else:
            imgs[topic][st] = bridge.imgmsg_to_cv2(m, 'passthrough')

    os.makedirs(args.out_dir, exist_ok=True)
    for st in sorted(targets):
        rel = st - t_first
        raw = imgs[f'{ns_list[0]}/image_input/compressed'].get(st)
        if raw is None:
            print(f't={rel:.2f}s: Raw 프레임 없음, 건너뜀')
            continue
        top, bottom = [_label(raw, f'raw  t={rel:.2f}s')], [np.zeros_like(raw)]
        for ns in ns_list:
            s = S[ns][st]
            name = ns.strip('/')
            mk = imgs[f'{ns}/mask'].get(st)
            dt = imgs[f'{ns}/image_annotated/compressed'].get(st)
            top.append(_label(mk if mk is not None else np.zeros(raw.shape[:2], np.uint8),
                              f"{name} mask ({s['mask_pixels']} px)"))
            det = f"area {s['area']:.0f}" if s['detected'] else 'no detection'
            bottom.append(_label(dt if dt is not None else np.zeros_like(raw), f'{name} {det}'))
        sheet = np.vstack([np.hstack(top), np.hstack(bottom)])
        path = os.path.join(args.out_dir, f'{args.prefix}_t{rel:06.2f}.png')
        cv2.imwrite(path, sheet)
        print(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('summary')
    s.add_argument('bag')
    s.add_argument('--t0', type=float)
    s.add_argument('--t1', type=float)
    e = sub.add_parser('export')
    e.add_argument('bag')
    e.add_argument('out_dir')
    e.add_argument('--at', type=float, nargs='+')
    e.add_argument('--prefix', default='frame')
    a = ap.parse_args()
    summary(a) if a.cmd == 'summary' else export(a)


if __name__ == '__main__':
    main()
