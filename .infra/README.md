# .infra – 개발자 문서

> 이 폴더는 **AWS 인프라 자동화** 파일을 모아 둔 내부용 디렉터리입니다. 일반 연구자는 건드릴 필요 없습니다.

---

## 📁 폴더 구성

```
.infra/
├── cloudformation-cpu.yml      # CPU 스택 + UserData
├── cloudformation-gpu.yml      # GPU 스택 (spot/ondemand 조건부)
├── deploy-cpu.sh              # CPU 배포 구현 스크립트
├── deploy-gpu.sh              # GPU 배포 구현 스크립트
├── setup_ssh_config.sh        # SSH 설정 스크립트
├── Dockerfile                 # 개발 컨테이너 이미지
└── README.md                  # (현재 문서)

# 프로젝트 루트의 Wrapper Scripts:
../deploy-cpu.sh               # CPU 배포 사용자 인터페이스
../deploy-gpu.sh               # GPU 배포 사용자 인터페이스
../setup-ssh.sh                # SSH 설정 사용자 인터페이스
```

## ⚡ 빠른 명령어 모음

### 🎯 권장 사용법 (Wrapper Scripts)

| 작업              | 명령                                                                                 | 설명                            |
| ----------------- | ------------------------------------------------------------------------------------ | ------------------------------- |
| CPU 배포 (기본)   | `../deploy-cpu.sh myproject --ssh-key id_ed25519_github_yourname`                    | t3.large, 50GB로 기본 배포      |
| CPU 배포 (커스텀) | `../deploy-cpu.sh myproject -k id_ed25519_github_yourname -i t3.xlarge -v 100`       | 인스턴스/볼륨 크기 커스터마이징 |
| GPU 배포 (SPOT)   | `../deploy-gpu.sh myproject --ssh-key id_ed25519_github_yourname --pricing spot`     | 60-90% 할인된 SPOT 인스턴스     |
| GPU 배포 (고정)   | `../deploy-gpu.sh myproject --ssh-key id_ed25519_github_yourname --pricing ondemand` | 안정적인 ON-DEMAND 인스턴스     |
| SSH 설정          | `../setup-ssh.sh myproject --ssh-key id_ed25519_github_yourname`                     | SSH 접속 간편화                 |

> 💡 **Wrapper 장점**:
>
> - 🔑 SSH 키 기반 자동 사용자 설정
> - ✅ 인자 검증과 사용자 확인 프롬프트
> - 📋 일관된 사용자 인터페이스
> - 💰 비용과 설정 정보 미리 확인
> - 📁 프로젝트 루트에서 바로 실행 가능

### 🔑 SSH 키 네이밍 시스템 (개발자 참고)

Wrapper 스크립트는 SSH 키 이름에서 사용자 이름을 자동 추출합니다:

```bash
# 패턴: id_[keytype]_[service]_[username]
KEY_NAME="id_ed25519_github_alice-kim"

# 추출 로직 (bash):
USERNAME=$(echo "$KEY_NAME" | sed 's/.*_\([^_]*\)$/\1/')
# → "alice-kim"

# 자동 설정:
DEV_USERNAME="alice-kim"                              # Docker 컨테이너 사용자
GIT_USER_NAME="alice-kim"                             # Git 설정
GIT_USER_EMAIL="alice-kim@users.noreply.github.com"  # Git 이메일
AWS_KEY_NAME="alice-kim-global-key"                   # EC2 KeyPair 이름
```

**검증 규칙:**

- 사용자 이름 부분에 underscore(`_`) 사용 금지 (hyphen `-` 권장)
- 키 파일 존재 여부 확인 (`.pub` 및 private key)
- 경로 지원: 키 이름 또는 full path 모두 가능

### 🔧 개발자용 직접 명령

| 작업               | 명령                                                                                 | 설명               |
| ------------------ | ------------------------------------------------------------------------------------ | ------------------ |
| 템플릿 문법 검사   | `aws cloudformation validate-template --template-body file://cloudformation-cpu.yml` | CFN 구문 오류 체크 |
| 스택 배포/업데이트 | ```bash                                                                              |

aws cloudformation deploy \
 --template-file cloudformation-cpu.yml \
 --stack-name test-dev-cpu \
 --parameter-overrides ProjectName=test SSHPublicKey="$(cat ~/.ssh/id_ed25519.pub)" \
 SSHPrivateKey="$(cat ~/.ssh/id_ed25519)" InstanceType=t3.large VolumeSize=50 \
 GitRepository=git@github.com:Q-BFD/QCBM-LSTM.git GitBranch=automation \
 --capabilities CAPABILITY_NAMED_IAM

````| 래퍼 스크립트 없이 직접 배포 |
| 스택 이벤트 확인 | `aws cloudformation describe-stack-events --stack-name test-dev-cpu --output table` | 진행 상황 실시간 확인 |
| 스택 삭제 | `aws cloudformation delete-stack --stack-name test-dev-cpu` | 롤백/정리 |

> ☝️ **팁**: `--no-fail-on-empty-changeset` 옵션을 넣으면 변경 사항이 없을 때도 명령이 실패하지 않습니다.

## 🛠 UserData 수정 시 주의
1. **변수 이스케이프**
   CloudFormation `Fn::Sub` 안에서는 `${VAR}` 를 CF 매크로로 인식합니다.
   Bash 변수는 **`$$VAR`** (또는 `$$var_name`) 형태로 써야 CF가 무시합니다.
2. 파일 크기가 커지면 IDE 에서 yaml 들여쓰기 깨지기 쉬우므로 VSCode *YAML* 플러그인 권장.
3. long-running 명령은 `timeout 1800 cmd` 형태로 래핑해 스택이 영구 대기하지 않도록 합니다.

## 🐞 디버깅 체크리스트
- **cloud-init**  상태 확인
  `sudo cloud-init status --long`
- UserData 전체 로그
  `sudo cat /var/log/cloud-init-output.log`
- **EBS 볼륨** 연결 확인
  `lsblk` / `df -h /mnt/data`
- **Docker 빌드 로그**
  `/var/log/${ProjectName}-setup.log` 에 `Docker image built successfully` 있는지 확인
- 설치 용량 부족 시
  `docker system prune -f` / `apt autoremove -y`

## 🧪 로컬 Docker 빌드 테스트
```bash
# 프로젝트 루트에서 실행
DOCKER_BUILDKIT=1 docker build -f .infra/Dockerfile -t qcbm-dev-test .
```

## 🔗 추가 학습 자료 (원래 README 개발자 참고)

- **AWS CLI 자주 쓰는 명령**
  - 현재 IAM/계정 확인 : `aws sts get-caller-identity`
  - KeyPair 목록 : `aws ec2 describe-key-pairs --output table`
  - S3 폴더 동기 : `aws s3 sync ./data s3://my-bucket/data`
- **CloudFormation 디버깅 팁**
  - 생성 실패 리소스만 보기
     `aws cloudformation describe-stack-events --stack-name $STACK \
--query 'StackEvents[?ResourceStatus==\`CREATE_FAILED\`].[LogicalResourceId,ResourceStatusReason]' --output table`
  - 템플릿 내부 변수 레퍼런스 검사 (bash → CF 충돌)
    `grep -n "\$[A-Z_][A-Z0-9_]*" cloudformation-cpu.yml | grep -v "\$\$"`
- **EC2 상태 확인 원라이너**
  ```bash
  ssh test "echo '=== Disk ==='; df -h; echo '=== Docker ==='; docker ps -a"
  ```

문의: 슬랙 #infra 또는 GitHub Issues.

## 📦 데이터 볼륨(50GB) 보존 전략
AWS Nitro 계열(t3, g4dn 등)에서는 `BlockDeviceMappings`로 **데이터 볼륨**을 직접 매핑하고
`DeleteOnTermination: false` 옵션을 주어 인스턴스가 사라져도 데이터를 보존합니다.

### CloudFormation 예시
```yaml
BlockDeviceMappings:
  - DeviceName: /dev/xvdf           # 부팅 시 → /dev/nvme1n1 로 보임
    Ebs:
      VolumeType: gp3
      VolumeSize: !Ref VolumeSize   # 기본 50 GiB
      DeleteOnTermination: false    # 인스턴스 Terminate 되어도 볼륨 유지
```

### 인스턴스 종료 후 데이터 살리기
1. **볼륨 ID 찾기**
   ```bash
   aws ec2 describe-volumes \
     --filters "Name=tag:Project,Values=test" \
     --query 'Volumes[0].VolumeId' --output text
   # → vol-0123456789abcdef0
   ```
2. **새 인스턴스에 붙이기**
   ```bash
   aws ec2 attach-volume \
     --volume-id vol-0123456789abcdef0 \
     --instance-id i-0abc... \
     --device /dev/xvdf
   ```
3. **마운트**
   ```bash
   ssh ubuntu@NEW_IP
   sudo mkdir -p /mnt/data
   sudo mount /dev/nvme1n1 /mnt/data
   df -h /mnt/data
   ```

> 루트 EBS는 기본적으로 `DeleteOnTermination: true`라 삭제됩니다. 필요하면 동일 옵션을 false 로 바꿔 전체 상태 스냅샷을 보존할 수 있습니다.
````
