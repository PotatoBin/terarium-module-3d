# DrawingSpinUp Rigging Server

이 디렉터리는 DrawingSpinUp 파이프라인을 웹 서비스 형태로 제공하기 위한 FastAPI 기반 서버 구현을 담고 있습니다. 애니메이션 및 렌더링 단계는 제외하고, 이미지 입력으로부터 리깅된 3D 모델을 생성하여 저장하는 데 초점을 맞추었습니다.

## 주요 기능
- 캐릭터 생성 및 메타데이터 저장
- 캐릭터별 이미지 업로드 및 작업 실행
- 단순화된 3D 메시(`.obj`), 리깅 데이터(`rig.json`), 텍스처(`albedo.png`), 미리보기(`preview.png`) 생성
- GPU가 여러 개인 환경에서의 작업 큐잉을 고려한 GPU 풀 구현
- `/data/characters/<id>/` 구조에 작업 결과 저장

## 실행 방법
```
uvicorn server.app.main:app --host 0.0.0.0 --port 8080
```

또는 Docker 이미지를 사용해 실행할 수 있습니다. 자세한 내용은 저장소 루트의 `README.md` 및 `Dockerfile`을 참고하세요.
