# Windows 설치 안내

이 프로젝트는 공식 ZIP 또는 Git 소스 폴더에서 실행하는 배포 방식만 지원합니다.
PyPI 게시나 `pip install` wheel 설치는 지원하지 않습니다.

이 문서는 보호자, 교사, 전산 담당자 또는 컴퓨터 사용에 익숙한 사람을 위한 최초
설치 안내입니다. 설치가 끝난 뒤 일반 사용자는 [초간단 사용법](QUICK_START_KO.md)의
네 단계만 따르면 됩니다.

## 설치 전에 알아둘 점

- 지원 환경: 64비트 Windows와 Python 3.12 프로젝트 환경
- 권장 설치 도구: `uv`
- 첫 준비 과정에는 인터넷 연결이 필요합니다.
- PyTorch·Torchvision 패키지와 COCO 자세 가중치 다운로드로 시간이 오래 걸릴 수
  있습니다.
- 모델 판별 화면은 로컬 컴퓨터에서 실행됩니다.
- 모델 파일은 `models/rescue79-hard4-portable-v1.pt`입니다.
- 시작 파일은 `START_RESCUE79.cmd`입니다.
- 실제 CCTV 연결이나 자동 신고 기능은 설치되지 않습니다.

조직 PC라면 프로그램 설치, 외부 다운로드와 사진 처리에 관한 내부 정책을 먼저
확인하세요.

## 1. 배포 파일 받기

GitHub 또는 GitLab의 공식 Release에서 Windows 배포 ZIP을 받습니다. 출처를 알 수
없는 재배포 파일은 사용하지 마세요.

가능하면 저장소의 녹색 **Code → Download ZIP**보다 모델과 필요한 파일이 함께 든
공식 Release 파일을 사용하세요. 소스 ZIP에는 대용량 모델이 빠질 수 있습니다.

다운로드 후 공개된 모델 SHA-256과 파일 해시를 확인합니다.

```powershell
Get-FileHash .\models\rescue79-hard4-portable-v1.pt -Algorithm SHA256
```

공개 모델 SHA-256은 다음과 같습니다.

```text
603cf711a4ccd59119c63a207bb78f3399ce8860c6eed5d6692481f13ff2db0a
```

출력된 값이 이 값과 한 글자라도 다르면 실행하지 말고 다시 다운로드하세요.

## 2. ZIP 전체 압축 풀기

ZIP 안에서 바로 실행하지 마세요. **모두 압축 풀기**를 선택합니다.

초보자에게는 다음처럼 짧은 로컬 경로를 권장합니다.

```text
C:\rescue79
```

다음 위치는 최초 시험에서 피하는 편이 좋습니다.

- 권한이 제한된 `Program Files`
- 동기화 중인 OneDrive 폴더
- 네트워크 공유 드라이브
- ZIP 내부
- 파일을 자동 삭제하는 임시 폴더

압축을 푼 뒤 다음 파일이 있는지 확인합니다.

```text
START_RESCUE79.cmd
models\rescue79-hard4-portable-v1.pt
pyproject.toml
uv.lock
README.md
MODEL_CARD.md
MODEL_LICENSE.md
THIRD_PARTY_NOTICES.md
```

## 3. uv 설치

이미 `uv --version`이 정상 출력되면 이 단계를 건너뜁니다.

Windows Package Manager를 사용할 수 있다면 PowerShell에서 다음 명령을 사용할 수
있습니다.

```powershell
winget install --id=astral-sh.uv -e
```

설치 방법이 바뀔 수 있으므로 최신 안내는 uv 공식 문서를 확인하세요.

<https://docs.astral.sh/uv/getting-started/installation/>

인터넷 설치 스크립트를 바로 실행하기 전에는 조직 정책과 스크립트 내용을 먼저
확인하세요. 설치 후 새 PowerShell 창을 열고 다음 명령으로 확인합니다.

```powershell
uv --version
```

## 4. Python 환경 준비

PowerShell을 열고 압축을 푼 폴더로 이동합니다.

```powershell
cd C:\rescue79
uv sync --frozen
```

`uv sync --frozen`은 `uv.lock`에 기록된 버전을 사용해 로컬 `.venv` 환경을
준비합니다. 필요한 Python 3.12가 없으면 uv가 내려받을 수 있습니다. 조직 정책상
자동 Python 다운로드가 금지돼 있다면 관리자가 Python 3.12를 별도로 준비해야
합니다.

환경 준비 중에는 창을 닫지 마세요. PyTorch 계열 패키지는 크기 때문에 시간이
걸릴 수 있습니다.

## 5. 첫 실행

파일 탐색기에서 `START_RESCUE79.cmd`를 더블클릭합니다. 또는 PowerShell에서 다음과
같이 실행합니다.

```powershell
.\START_RESCUE79.cmd
```

검은색 창을 닫지 말고 기다립니다. 첫 실행에서는 Torchvision의 COCO 사람 자세
가중치를 내려받을 수 있습니다. 이 자세 가중치는 hard4 모델에 포함되지 않은 별도
파일입니다.

브라우저에 **Rescue79 정적 7·9 모델 검토기**가 열리고 “준비되었습니다”라는
안내가 표시되면 설치가 끝난 것입니다.

## 6. 설치 확인 시험

개인정보가 없는 제공 예제나 생성형 시험사진을 사용합니다.

1. 화면에 “준비되었습니다”가 표시되는지 확인합니다.
2. 알려진 정답 7 또는 9를 선택합니다.
3. PNG, JPG 또는 WEBP 한 장을 선택합니다.
4. **모델 검토 시작**을 누릅니다.
5. 원본과 관절 오버레이가 모두 표시되는지 확인합니다.
6. 결과가 정답·오답·판정 보류 중 하나로 설명되는지 확인합니다.

설치 확인을 위해 실제 CCTV 원본이나 민감한 개인정보 사진을 사용할 필요는
없습니다.

## 7. 일반 사용자에게 전달하기

최초 준비를 마친 뒤 바탕화면에 `START_RESCUE79.cmd`의 바로가기를 만들어 줄 수
있습니다. 바로가기 이름은 다음처럼 쉽게 정하세요.

```text
7·9 사진 검토기 시작
```

일반 사용자에게는 다음 세 문서를 함께 전달하세요.

- [초간단 사용법](QUICK_START_KO.md)
- [결과 읽는 법](RESULT_GUIDE_KO.md)
- [안전과 개인정보](SAFETY_AND_PRIVACY_KO.md)

## 인터넷을 끊고 사용할 때

다음 항목은 인터넷이 연결된 상태에서 미리 끝내야 합니다.

- `uv sync --frozen`
- 프로그램 최초 실행
- COCO 자세 가중치 다운로드 완료
- 예제 이미지 판별 확인

그 뒤 네트워크를 끊고 다시 실행해 정상 작동하는지 시험하세요. “로컬 실행”은
기본 서버가 외부에 공개되지 않는다는 뜻이며, 아무 준비 없이 첫 실행부터 완전한
오프라인이라는 뜻은 아닙니다.

## 업데이트 방법

기존 폴더 위에 새 Release를 덮어쓰지 마세요.

1. 새 버전을 다른 폴더에 압축 해제합니다.
2. 새 Release의 해시를 확인합니다.
3. 새 폴더에서 환경을 준비합니다.
4. 예제 이미지로 시험합니다.
5. 문제가 없을 때 바로가기를 새 폴더로 변경합니다.
6. 이전 버전은 되돌리기가 끝날 때까지 보존합니다.

사용자 사진이나 실제 CCTV 자료를 프로그램 폴더 안에 보관하지 마세요.

## 제거 방법

프로그램이 실행 중이면 검은색 창에서 `Ctrl + C`를 눌러 먼저 종료합니다. 이
프로젝트 전용 폴더를 삭제하면 프로젝트 코드와 `.venv`가 제거됩니다.

Torchvision 자세 가중치와 uv 캐시는 사용자 캐시 폴더에 별도로 남을 수 있습니다.
다른 Python 프로젝트도 같은 캐시를 사용할 수 있으므로 무작정 삭제하지 말고
담당자가 확인하세요.

## 공개 배포 담당자 확인표

- [ ] 깨끗한 Windows PC에서 최초 설치 확인
- [ ] 모델 내부에 개발 PC 절대경로가 남지 않았는지 확인
- [ ] `models/rescue79-hard4-portable-v1.pt` 자동 로딩 확인
- [ ] 모델 SHA-256 `603cf711...ff2db0a`가 코드·문서와 일치
- [ ] PNG·JPG·WEBP 판별 확인
- [ ] 한 사람·다중 인물·가림 사례 확인
- [ ] 설치 후 인터넷을 끊고 재실행 확인
- [ ] 한글 경로와 영문 경로에서 실행 확인
- [ ] `LICENSE`, `MODEL_LICENSE.md`, `MODEL_CARD.md` 포함 확인
- [ ] 제3자 COCO 자세 가중치를 배포 ZIP에 넣지 않았는지 확인
- [ ] 실제 CCTV 100%, 오경보 0%, 자동 신고 같은 문구가 없는지 확인

문제가 생기면 [문제 해결](TROUBLESHOOTING_KO.md)을 참고하세요.
