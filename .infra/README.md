# .infra – 개발자 문서

> 이 폴더는 **AWS 인프라 자동화** 파일을 모아 둔 내부용 디렉터리입니다. 일반 연구자는 건드릴 필요 없습니다.

---

## 📁 폴더 구성

```
.infra/
├── cloudformation-cpu.yml   # CPU 스택 + UserData
├── cloudformation-ondemand.yml / spot.yml
├── deploy-cpu.sh            # 로우레벨 배포 스크립트
├── setup_ssh_config.sh      # SSH 설정 스크립트
├── Dockerfile               # 개발 컨테이너 이미지
└── README.md                # (현재 문서)
```

## ⚡ 빠른 명령어 모음

| 작업               | 명령                                                                                 | 설명               |
| ------------------ | ------------------------------------------------------------------------------------ | ------------------ |
| 템플릿 문법 검사   | `aws cloudformation validate-template --template-body file://cloudformation-cpu.yml` | CFN 구문 오류 체크 |
| 스택 배포/업데이트 | ```bash                                                                              |

aws cloudformation deploy \
 --template-file cloudformation-cpu.yml \
 --stack-name test-dev-cpu \
 --parameter-overrides ProjectName=test KeyName=test-dev-key VolumeSize=50 \
 GitRepository=https://github.com/Q-BFD/QCBM-LSTM.git GitBranch=automation \
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
````

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
