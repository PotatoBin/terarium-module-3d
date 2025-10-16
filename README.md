# Terarium Module 3D – DrawingSpinUp Rigging Service

이 저장소는 DrawingSpinUp 파이프라인을 기반으로 이미지 입력을 받아 리깅된 3D 모델을 생성하는 서버 및 Docker 환경을 제공합니다. RTX 2080 Ti 여러 대가 장착된 환경에서도 즉시 사용할 수 있도록 GPU 풀링 로직과 자동화된 리소스 다운로드 스크립트를 포함합니다.

## 구성 요소
- `server/`: FastAPI 기반 API 서버 소스 코드
- `DrawingSpinUp/`: 원본 프로젝트 연동 정보 및 자산 매니페스트
- `scripts/download_drawing_spinup_assets.py`: `assets_manifest.yaml`에 정의된 외부 자산을 자동 다운로드
- `Dockerfile`: GPU 지원 Docker 이미지 정의
- `docker-compose.yml`: 개발 및 운영 환경에서 사용할 수 있는 예제 컴포즈 파일

## 데이터 디렉터리 구조
서버는 기본적으로 `/data` 디렉터리를 사용하며, 캐릭터별 구조는 다음과 같습니다.

```
/data/
└── characters/
    └── <character-id>/
        ├── character.json
        ├── inputs/
        │   └── <job-id>/
        │       └── source.png
        └── outputs/
            └── <job-id>/
                ├── model.obj
                ├── rig.json
                ├── albedo.png
                └── preview.png
```

## 로컬 개발
1. 의존성 설치
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r server/requirements.txt
   ```

2. DrawingSpinUp 자산 다운로드
   ```bash
   python scripts/download_drawing_spinup_assets.py
   ```
   `DrawingSpinUp/assets_manifest.yaml` 파일을 프로젝트 환경에 맞게 수정하세요.

3. 서버 실행
   ```bash
   uvicorn server.app.main:app --host 0.0.0.0 --port 8080
   ```

## Docker 이미지 빌드
```bash
docker build -t drawing-spinup-rigging:latest .
```

이미지는 CUDA 런타임을 기반으로 하며, 빌드 과정에서 자동으로 자산 다운로드 스크립트를 실행합니다. 여러 대의 RTX 2080 Ti가 설치된 환경이라면 `docker run` 실행 시 `--gpus all` 옵션을 사용하고, `SERVER_GPU_IDS` 환경 변수를 통해 사용 가능한 GPU 목록을 지정할 수 있습니다.

## docker-compose 예시
`docker-compose.yml` 파일에는 아래와 같은 구성이 포함되어 있습니다.

```yaml
services:
  rigging:
    build: .
    image: drawing-spinup-rigging:latest
    ports:
      - "8080:8080"
    environment:
      SERVER_GPU_IDS: "[0,1,2,3]"
      DATA_ROOT: "/data"
    volumes:
      - ./data:/data
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
```

## API 요약
- `POST /characters` – 캐릭터 프로필 생성
- `GET /characters` – 캐릭터 목록과 최신 작업 조회
- `POST /characters/{character_id}/jobs` – 이미지 업로드 및 리깅 작업 실행
- `GET /healthz` – 헬스 체크

## 주의사항
- 현재 파이프라인은 실제 모델 추론 대신 단순화된 메시와 리깅 데이터를 생성합니다. 실서비스에서는 DrawingSpinUp의 실제 네트워크와 가중치를 연동하세요.
- 자산 다운로드를 위한 URL과 체크섬은 보안 정책에 따라 별도로 관리해야 합니다.
