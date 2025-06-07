# QCBM-LSTM

> Quantum Circuit Born Machine(QCBM)-과 Long Short-Term Memory(LSTM) 를 결합한 **하이브리드 양자-클래식** 모델 연구 프로젝트입니다.

---

## 🔬 연구자(Regular User) 빠른 시작

1️⃣ **EC2 개발 환경 자동 배포**

```bash
./deploy-cpu.sh qcbm          # 프로젝트 이름은 자유롭게 지정 가능
```

2️⃣ **SSH 설정**

```bash
./setup-ssh.sh qcbm           # 30초 이내
```

3️⃣ **접속 & 개발**

```bash
ssh qcbm-container            # Docker 컨테이너 내부 셸
```

| 서비스       | 주소 / 명령                          | 용도           |
| ------------ | ------------------------------------ | -------------- |
| Jupyter      | http://<EIP>:8888 (token :qcbmtoken) | 노트북 실행    |
| VSCode Web   | http://<EIP>:8080                    | 브라우저 IDE   |
| EC2 SSH      | `ssh qcbm`                           | 서버 관리      |
| 컨테이너 SSH | `ssh qcbm-container`                 | 코드 작성·실험 |

> ⏱ 설치 5-8분 소요, 비용 ≈ $0.09/시간 (t3.large + 50 GB EBS)

### 💻 로컬 실행 (선택 사항)

```bash
pip install -r requirements.txt
jupyter notebook               # 로컬 노트북
```

### 📁 프로젝트 구조

```
QCBM-LSTM/
├── src/ , notebooks/          # 연구 코드·노트북
├── data/ , results/           # 데이터셋·출력
├── deploy-cpu.sh              # 원클릭 배포 래퍼
├── setup-ssh.sh               # SSH 설정 래퍼
└── .infra/                    # 인프라 자동화 (무시해도 됨)
```

> 💡 **Tip** : 사용하지 않을 때 EC2 인스턴스를 중지하면 비용을 절감할 수 있습니다.

---

## 🛠 개발자 문서

인프라를 수정해야 할 경우 **`.infra/README.md`** 를 참고하세요.

---

## 라이선스

MIT
