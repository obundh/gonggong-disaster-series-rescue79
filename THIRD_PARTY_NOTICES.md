# 제3자 소프트웨어·모델·자산 고지

이 문서는 Rescue79 공개 소스와 모델 실행에 관계된 제3자 구성요소의 경계를
설명합니다. 프로젝트 자체 소스와 `models/rescue79-hard4-portable-v1.pt`에는
저장소의 `LICENSE`와 `MODEL_LICENSE.md`가 적용됩니다. 저장소에 포함된 생성형
만화·시험 캡처·예제의 프로젝트 소유자 허가 범위는 `ASSET_LICENSE.md`에 별도로
적었습니다. 이 허가는 제3자 플랫폼 약관이나 제3자 권리를 바꾸지 않습니다.
제3자 항목은 각각의 원 라이선스와 이용조건이 우선합니다.

## 배포 형태

기본 Git 저장소와 소스 Release는 Python 가상환경 `.venv`, 제3자 wheel·DLL,
Torchvision COCO 자세 가중치를 포함하지 않는 것을 원칙으로 합니다. 사용자의
환경에서 `uv`가 잠금파일에 따라 의존성을 설치합니다.

실행 파일, 오프라인 Python 환경 또는 wheel을 포함한 별도 배포물을 만들 때는
실제로 포함된 모든 직접·전이 의존성의 라이선스 전문과 고지를 다시 수집해야
합니다. 이 문서만 복사하는 것으로 바이너리 재배포 의무가 모두 충족되는 것은
아닙니다.

## 주요 Python 런타임 구성요소

정확한 버전은 배포본의 `uv.lock`을 기준으로 합니다.

| 구성요소 | 사용 범위 | 주요 라이선스 | 원본 |
| --- | --- | --- | --- |
| PyTorch | TCN 모델 추론 | Apache-2.0 및 포함 구성요소 고지 | <https://github.com/pytorch/pytorch> |
| Torchvision | 사람·COCO-17 관절 추출 | BSD-3-Clause | <https://github.com/pytorch/vision> |
| FastAPI | 로컬 HTTP 애플리케이션 | MIT | <https://github.com/fastapi/fastapi> |
| Uvicorn | 로컬 ASGI 서버 | BSD-3-Clause | <https://github.com/encode/uvicorn> |
| NumPy | 수치 연산 | BSD-3-Clause 및 포함 구성요소 고지 | <https://github.com/numpy/numpy> |
| OpenCV Python headless | 평가와 동일한 이미지 축소 | Apache-2.0 및 포함 구성요소 고지 | <https://github.com/opencv/opencv-python> |
| Pillow | 이미지 표현·렌더링 | HPND 계열 Pillow License | <https://github.com/python-pillow/Pillow> |
| python-multipart | 로컬 폼 파일 업로드 파싱 | Apache-2.0 | <https://github.com/Kludex/python-multipart> |
| uv | Python·의존성 환경 준비 도구 | MIT 또는 Apache-2.0 | <https://github.com/astral-sh/uv> |

시험 환경에만 사용하는 `pytest`, `httpx2` 등 개발 의존성은 일반 사용자 실행
경로에 필요하지 않습니다. 정확한 개발 의존성 버전과 원 출처는 `uv.lock`을
기준으로 하며, 이를 포함한 바이너리를 재배포할 때는 각 패키지 고지를 별도로
수집해야 합니다.

설치된 패키지 버전의 라이선스 파일이 이 표보다 우선합니다.

## Torchvision COCO 자세 가중치

RGB 사진에서 COCO-17 관절을 추출하기 위해 다음 사전학습 가중치를 별도로
사용합니다.

- 구현: Torchvision `keypointrcnn_resnet50_fpn`
- 가중치 enum: `KeypointRCNN_ResNet50_FPN_Weights.COCO_V1`
- 공식 URL:
  <https://download.pytorch.org/models/keypointrcnn_resnet50_fpn_coco-fc266e95.pth>
- 확인된 SHA-256:
  `fc266e953d2b302cdcbb9ae66f71f6b0d4649928bf02dc573961e361e4918926`
- 파일 크기: 237,034,793 bytes
- 학습 데이터 표기: COCO train2017 person keypoints
- Torchvision 코드 라이선스: BSD-3-Clause

이 파일은 다음 항목에 포함되지 않습니다.

- `models/rescue79-hard4-portable-v1.pt`
- 기본 Git 소스
- 프로젝트 MIT 재허가 범위

Torchvision 공식 문서는 사전학습 가중치가 학습 데이터에서 유래한 별도 조건을
가질 수 있으므로 사용자가 이용 목적에 맞는 권리를 확인해야 한다고 안내합니다.
따라서 자세 가중치를 직접 넣은 오프라인 Release는 별도 검토 없이 배포하지
않습니다.

## COCO 데이터셋

프로젝트는 COCO 데이터셋 자체를 저장소에 포함하거나 재배포하지 않습니다.
Torchvision 자세 가중치가 COCO train2017 person keypoints에서 학습됐다는 출처를
표시합니다.

COCO 데이터, 이미지, 주석 또는 파생물을 별도로 내려받아 사용하려면 COCO와 각
원본 이미지의 적용 조건을 사용자가 확인해야 합니다.

## 생성형 학습·시험 이미지

hard4 적응 학습과 50장 검증에는 생성형 정지이미지가 사용됐습니다. 이 공개 모델
패키지의 MIT License는 생성 서비스의 약관, 제3자 유사성, 상표·초상·개인정보
권리를 대신 판단하거나 재허가하지 않습니다.

생성형 자료를 공개할 때는 다음을 기록하세요.

- 사용한 생성 서비스와 생성 시점
- 생성형 자료임을 알리는 표시
- 학습자료, 평가자료와 설명용 만화의 구분
- 실제 사람·기관·상표와 혼동될 가능성 검토
- 해당 서비스의 공개·상업 이용조건 확인

50장 검증용 이미지는 실제 CCTV가 아니며 실제 사람의 구조 상황을 기록한 자료가
아닙니다.

## 설명용 고양이 만화

`docs/comics`의 고양이 만화는 생성형 이미지로 만든 설명 자료입니다. 모델 학습
입력이나 독립 성능평가 자료가 아닙니다.

만화의 고양이, 관제실과 사고 장면은 설명을 위한 가상 표현이며 실제 사람·기관·사건
또는 제품 승인을 나타내지 않습니다. 그림 속 UI 캡처 부분은 프로젝트의 로컬
검토기와 시험 결과를 설명하기 위해 사용됐습니다.

생성형 이미지의 철자·수치·시각 묘사는 오류가 있을 수 있으므로 정확한 사실은
README와 `MODEL_CARD.md`의 텍스트를 우선합니다.

## 글꼴과 운영체제 자산

웹 화면은 사용자의 운영체제에 설치된 시스템 글꼴 이름을 참조할 수 있습니다.
Windows 시스템 글꼴을 저장소에 복사하거나 재배포하지 않습니다.

향후 별도 글꼴 파일을 번들하면 해당 글꼴의 저작권 고지와 라이선스 전문을 함께
제공해야 합니다.

## 기관 비제휴 고지

이 프로젝트는 정부기관, 군, 경찰, 소방, 의료기관 또는 CCTV 제조사의 승인·인증·
보증·제휴 제품이 아닙니다. 기관 로고, 문장, 긴급서비스 표장 또는 제3자 상표를
허가 없이 포함하지 않습니다.

`112`, `119`, CCTV와 구조신호에 대한 언급은 기능 경계와 적용 맥락을 설명하기
위한 것이며 해당 기관의 승인을 의미하지 않습니다.

## 재배포 담당자 확인표

- [ ] 실제 포함 파일을 기준으로 라이선스 재검사
- [ ] `uv.lock`과 설치 패키지 목록 보존
- [ ] 모든 wheel·DLL의 라이선스 전문 수집
- [ ] COCO 자세 가중치를 기본 ZIP에 포함하지 않음
- [ ] 자세 가중치 URL·SHA-256·학습 데이터 출처 표시
- [ ] 실제 설치된 직접·전이 의존성의 라이선스 파일 수집
- [ ] 생성형 이미지의 생성 서비스와 이용조건 확인
- [ ] 모델·소스·제3자 자산의 라이선스 범위를 분리
- [ ] 실제 기관 승인이나 제휴로 오인할 표현 제거

## 프로젝트 라이선스와의 관계

프로젝트 소스와 hard4 모델 가중치에는 `LICENSE`와 `MODEL_LICENSE.md`의 MIT 조건이
적용됩니다. 이 MIT 허가는 제3자 구성요소의 원 라이선스를 변경하지 않습니다.
