# Rescue79 모델 라이선스

Copyright (c) 2026 obundh

## MIT로 공개하는 범위

프로젝트 소유자는 다음 hard4 모델 가중치 파일을 이 저장소의 `LICENSE`에 수록된
MIT License 조건으로 공개합니다.

```text
models/rescue79-hard4-portable-v1.pt
```

이 허가는 해당 파일에 들어 있는 프로젝트 작성 모델 메타데이터와 학습된 hard4
파라미터에 적용됩니다. 현재 공개 파일은 다음 SHA-256으로 식별합니다.

```text
603cf711a4ccd59119c63a207bb78f3399ce8860c6eed5d6692481f13ff2db0a
```

프로젝트가 작성한 소스코드도 별도 표기가 없는 한 저장소의 `LICENSE`에 수록된 MIT
License 조건을 따릅니다.

## 재배포 시 지켜야 할 조건

MIT License에 따라 위 모델 파일을 복사·수정·배포할 수 있습니다. 재배포물에는
다음을 함께 제공하세요.

- 저장소의 `LICENSE`
- 이 `MODEL_LICENSE.md`
- `MODEL_CARD.md`
- `THIRD_PARTY_NOTICES.md`
- 원 저작권 고지
- 수정했다면 원본과 수정본을 구분하는 버전·해시 기록

모델을 수정한 뒤에도 원래 모델의 이름과 해시를 그대로 사용하면 안 됩니다. 새
파일명, 새 버전, 새 SHA-256과 변경 내용을 기록하세요.

## MIT 범위에 포함되지 않는 항목

이 모델 라이선스는 다음 항목을 재허가하지 않습니다.

- Torchvision `KeypointRCNN_ResNet50_FPN_Weights.COCO_V1` 자세 가중치
- PyTorch, Torchvision, NumPy, Pillow, FastAPI, Uvicorn 등 제3자 소프트웨어
- COCO 데이터셋과 제3자 학습 데이터
- 사용자가 업로드한 이미지와 실제 CCTV 영상
- `ASSET_LICENSE.md`가 적용되지 않는 글꼴, 디자인, 캐릭터와 시각 자산
- 생성 서비스의 별도 약관이나 제3자 권리가 적용되는 범위
- 상표, 초상, 개인정보 또는 퍼블리시티권

제3자 항목에는 각각의 원 라이선스와 이용조건이 우선합니다. 자세한 내용은
`THIRD_PARTY_NOTICES.md`를 확인하세요.

## 자세 가중치와의 관계

hard4 파일은 RGB 원본 사진이나 COCO 자세 가중치를 내부에 포함하지 않습니다.
프로그램이 RGB 사진을 처리할 때 Torchvision 자세 가중치를 별도로 내려받아
COCO-17 관절을 추출합니다.

프로젝트의 MIT License는 해당 Torchvision 가중치, COCO 데이터셋 또는 그 밖의
제3자 권리를 MIT로 바꾸지 않습니다. 자세 가중치를 직접 포함한 오프라인 번들을
배포하려면 별도의 권리·라이선스 검토가 필요합니다.

## 안전 경계와 라이선스의 관계

`MODEL_CARD.md`의 연구용 범위와 안전 안내는 모델의 검증 상태를 정확히 전달하기
위한 것입니다. MIT License의 허가 범위를 축소하는 추가 라이선스 제한은 아닙니다.

다만 MIT 허가가 다음을 의미하지는 않습니다.

- 실제 CCTV 성능 인증
- 구조 요청 또는 사람의 의도 판정 보증
- 자동 신고·출동 승인
- 국가기관·군·경찰·소방·의료기관의 승인 또는 제휴
- 관련 법률·개인정보·안전 의무 면제

사용자는 자신의 용도에 맞는 법적 권리, 안전성, 개인정보 보호, 실제 성능과 제3자
조건을 직접 확인해야 합니다.

## 무보증

모델과 소프트웨어는 MIT License의 무보증 조건에 따라 “있는 그대로” 제공됩니다.
정확성, 완전성, 실제 CCTV 일반화, 응급상황 판단, 특정 목적 적합성 또는 비침해를
보증하지 않습니다.

현재 알려진 성능 경계:

- 사전 고정 생성형 7·9 정지사진: 50/50
- 실제 CCTV 검출률: 미측정
- 실제 오경보율: 미측정
- 완전한 `7→9→7→9` 시간 순서: 미검증
- 자동 외부 신고: 없음

성능 수치를 재배포할 때는 위 범위를 함께 표시해야 오해를 줄일 수 있습니다.

## 권장 저작권 표시 예시

```text
Rescue79 hard4 portable v1
Copyright (c) 2026 obundh
Licensed under the MIT License.
Generated-still diagnostic model; real-CCTV detection and false-positive rates are unmeasured.
```
