# 모듈 1 — 임베디드 제어 기초

박준명의 모듈 1 실험 환경·실행 절차와 증거 목록이다. 설정·측정·해석은 [보고서](report.md)에 정리했다.

## 환경과 소스 변경

| 항목 | 구성 |
|---|---|
| 라즈베리파이 | `pa01`, Ubuntu Server 22.04 구성, OS 출력 Ubuntu 22.04.5 LTS, `aarch64` |
| 사용자·USB 포트 | `pa01`, `dialout` 그룹 / `/dev/ttyACM0`, `root:dialout`, `crw-rw----` |
| 제어기·모터 | OpenCR 1.0 / XM430-W210(1030), ID 1, 모터 1개 |
| 통신 | USB 시리얼 115200 bps / 모터 1 Mbps, Protocol 2.0 |
| PC 역할 | SSH 접속. 업로드·시리얼 송수신·로그 저장은 라즈베리파이에서 수행 |

과제 자료의 [P 제어 예제 사본](examples/opencr_position_p/opencr_position_p.ino)을 수정했다. `DXL_ID`를 12에서 1로, 모델 검사·메시지·주석을 XM430-W350에서 XM430-W210으로 변경했다. 모델 번호 1030은 [ROBOTIS 공식 모델 표](https://emanual.robotis.com/docs/kr/dxl/x/xm430-w210/)로 확인했다. 통신 설정, 펌웨어 버전 38 이상·Drive Mode 검사, 제어 계산과 정지 처리는 유지했다.

수정 소스와 Kp 0.5·목표각 10°·명령 속도 상한 5°/s 조합은 이번 장비에서 빌드·업로드·실행한 결과를 기록했다. 실행 전 과제용으로 검증된 조합이라는 별도 근거는 확보하지 못했다. 모터 펌웨어의 정확한 버전 번호도 기록하지 못했다.

## 빌드 및 업로드

다음은 라즈베리파이에 Arduino CLI와 OpenCR 코어를 설치하고 수정 소스를 `~/opencr-diagnosis/opencr_position_p`에 둔 상태에서 사용한 명령이다. 기존 제공 `.bin` 대신 수정 소스로 새로 빌드한 파일을 사용했다.

```bash
export OPENCR_BUILD="$HOME/pa-opencr-build"
export OPENCR_OUTPUT="$HOME/opencr-diagnosis/build-$(date +%Y%m%d-%H%M%S)"
set -o pipefail

"$OPENCR_BUILD/bin/arduino-cli" \
  --config-file "$OPENCR_BUILD/arduino-cli.yaml" \
  compile \
  --fqbn ROBOTIS:OpenCR:OpenCR \
  --jobs 1 \
  --output-dir "$OPENCR_OUTPUT" \
  "$HOME/opencr-diagnosis/opencr_position_p" \
  2>&1 | tee "$HOME/opencr-diagnosis/build.log"
```

빌드 결과는 프로그램 104,296 bytes(13%), 전역 변수 40,620 bytes다. 실행 당시 출력 디렉터리는 `/home/pa01/opencr-diagnosis/build-20260921-172723`이었다. 이후 새 셸에서 기존 파일을 사용할 경우 `OPENCR_OUTPUT`을 이 경로로 지정한다.

업로더와 파일·포트 확인:

```bash
UPLOADER="$HOME/pa-opencr-build/uploader-src/arduino/opencr_develop/opencr_ld/opencr_ld"

if [ ! -x "$UPLOADER" ]; then
  UPLOADER="$HOME/opencr-uploader-src/arduino/opencr_develop/opencr_ld/opencr_ld"
fi

ls -l "$UPLOADER" /dev/ttyACM0
ls -lh "$OPENCR_OUTPUT/opencr_position_p.ino.bin"
```

시리얼 모니터를 종료하고 파일·포트가 확인된 상태에서 업로드했다.

```bash
set -o pipefail
"$UPLOADER" /dev/ttyACM0 115200 \
  "$OPENCR_OUTPUT/opencr_position_p.ino.bin" 1 \
  2>&1 | tee "$HOME/opencr-diagnosis/upload.log"
```

`opencr_ld 1.0.4`에서 보드 `OpenCR R1.0`을 인식했고, `CRC OK 9B81E2 9B81E2`, `[OK] Download`, `jump finished`를 확인했다. 업로더의 크기 표시는 102 KB, `ls -lh`에서는 103K였다.

## 시리얼 설정·실행·기록

라즈베리파이에서 다음 명령으로 연결했다.

```bash
python3 -m serial.tools.miniterm /dev/ttyACM0 115200 --eol LF -e
```

모니터 안에서 `k 0.5`, `v 5`, `a 10`을 각각 입력해 설정 응답을 확인했다. 이 명령들은 설정만 변경한다. `READY` 출력은 확보하지 못했으나 정상 `P SET` 응답과 이후 측정 로그를 확보했다.

실행 로그를 저장하기 위해 안내된 명령은 다음과 같다. 기존 모니터에서 `Ctrl+]`로 나온 뒤 라즈베리파이 셸에서 실행한다.

```bash
script -q -f -c \
  "python3 -m serial.tools.miniterm /dev/ttyACM0 115200 --eol LF -e" \
  "$HOME/opencr-diagnosis/실행A.log"
```

모터 고정·이동 여유·전원 차단 위치를 확인한 상태에서 사용하는 실행 명령 형식은 `s <Kp> <속도상한_deg_s> <상대목표각_deg>`다. 실행 A의 안내 명령은 `s 0.5 5 10`이며, 저장한 로그에는 명령 자체와 START 행이 없지만 Kp·목표각·속도 상한은 측정 행에서 확인된다. 시작 위치를 0°로 삼고 2초 후 목표가 10°로 변경됐다.

`x` 입력 후 `STOP: user`와 실제 모터 정지를 확인했다. 코드상 목표 속도 0·토크 해제 호출이 성공한 응답이며, SSH나 모니터 종료를 정지 수단으로 사용하지 않는다. 모니터 종료는 `Ctrl+]`다.

## 기록 범위와 해석 참고

- 실행 로그는 전달한 첨부 원문을 그대로 보존했다. 0.200~12.402초 측정 123행(목표 변경 후 105행), 정지·터미널 종료 기록을 포함한다. 실행 명령·START·READY 행과 정확한 정지 경과 시간은 없다.
- 2.000초 행의 일부 필드 사이 탭이 누락됐지만 필드명과 수치는 식별 가능하다. 보고서 표는 이 값을 사용했다.
- `dt_ms`는 기록된 제어 간격으로 10.000~10.003 ms다. `t_s`는 실행 시작 이후 경과 시간이다.
- 명령 속도 상한 5°/s는 raw 단위 변환으로 최대 출력 4.122°/s가 됐다. 측정 속도는 별개의 값이며 2.300초에는 5.496°/s가 기록됐다.
- 빌드 로그는 성공 출력 2행이다. 최초 파일 확인 로그의 일부 경로는 이후 업로드 전 확인 기록으로 보완했다.
- 환경 기록은 확인 명령별로 구분했으며, 전달 과정에서 링크가 된 OS 정보의 URL은 일반 문자열로 복원했다.

## 결과 파일

| 파일 | 내용 |
|---|---|
| [report.md](report.md) | 문제 1~4 답안 및 A·B 실측 비교 |
| [환경확인.txt](results/환경확인.txt) | 호스트명·OS·아키텍처·포트·접근 그룹 |
| [diagnostic_scan.log](results/diagnostic_scan.log) | 모델 1030·ID 1·1 Mbps·Protocol 2.0 검색 결과 |
| [build.log](results/build.log) | 수정 소스 빌드 성공 출력 |
| [build_artifact.log](results/build_artifact.log) | 최초 `.bin` 파일 확인 출력 |
| [upload_precheck.log](results/upload_precheck.log) | 업로더·포트·바이너리 전체 경로 확인 |
| [upload.log](results/upload.log) | 실제 업로드 성공 출력 |
| [settings.log](results/settings.log) | Kp 0.5·속도 상한 5°/s·목표각 10° 설정 응답 |
| [실행A.log](results/실행A.log) | 초기·중간·마지막 측정값과 `STOP: user` |
| [실행B.log](results/실행B.log) | Kp 1.0의 시작·설정 응답, 측정 92행과 `STOP: user` |

## 문제 2~4 진행 상태

- 문제 2: 실행 A의 세 시점 오차·피드백 경로·보정 방향 작성 완료.
- 문제 3: Kp 0.5·1.0의 A·B 실측 비교 및 게인·I·D 설명 작성. 축에 외부 부하가 없음을 확인했다. 물리적 시작 각도 일치 기록은 없고 B의 실제 정지 확인은 대기 중이며, 두 Kp의 사전 검증 근거는 없다.
- 문제 4: 발제문의 가상 기록을 바탕으로 구조도·송수신 역할·주기 계산·통신 단절 정책 작성 완료. 실제 micro-ROS 환경은 구축하지 않았다.

### 실행 B 절차와 기록

1. 발제문에는 두 번째 Kp 수치가 명시돼 있지 않다. B는 Kp 1.0을 비교 실험용으로 제안했으며, A의 0.5와 B의 1.0 모두 과제용 사전 검증 근거를 별도 확보하지 못했다.
2. A와 같은 장비·소스·부하·시작 자세·이동 여유를 맞춘다. 상대각을 매번 0으로 잡는 것만으로 물리적 시작 자세가 같아지는 것은 아니다. 시작 자세를 재현하지 못하면 조건 차이를 기록하고 비교 한계로 표시한다.
3. 목표각 10°, 명령 속도 상한 5°/s, 제어 요청 10 ms·로그 100 ms를 유지한다. Kp는 시리얼 명령으로 변경하므로 소스를 다시 빌드할 필요는 없다.
4. A 로그를 보존하고 별도 B 로그로 기록한다. 다음 명령은 기록용 모니터만 열며 모터를 구동하지 않는다.

```bash
OPENCR_B_LOG="$HOME/opencr-diagnosis/실행B-$(date +%Y%m%d-%H%M%S).log"
script -q -f -c \
  "python3 -m serial.tools.miniterm /dev/ttyACM0 115200 --eol LF -e" \
  "$OPENCR_B_LOG"
```

5. 제안한 Kp 1.0과 시작 조건으로 실행할 때에는 `s 1.0 5 10`을 입력한다. 이 명령은 실제 모터를 구동한다. 시작·설정 응답부터 15초 정도 기록하고 `x`로 정지 응답 및 실제 정지를 확인한다.
6. 실제 Kp, 부하·시작 자세 조건, B 로그를 보고서에 반영한 뒤 동일 경과 시간의 A·B 측정값과 목표 초과 여부를 비교한다.

B 로그는 첨부 원문 그대로 저장했다. 첫 실행 명령은 `Invalid setting`으로 거부됐고 재입력 후 START·정상 설정 응답이 나왔다. 측정 92행(목표 변경 후 73행)과 `xSTOP: user`가 있으며, 마지막 측정은 9.200초다. 안내한 약 15초보다 짧게 기록됐으므로 A와 공통으로 확보한 9초 이내 표본을 비교했다.

물리적 시작 조건·실제 정지 확인을 마무리한 뒤 모듈 1 최종 제출 태그를 검토한다.
