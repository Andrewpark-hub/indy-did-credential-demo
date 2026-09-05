# Hyperledger Indy 기반 자기주권신원(SSI) DID/VC/VP 자격증명 시스템

![Python](https://img.shields.io/badge/Python-3.6%2B-blue?style=flat-square&logo=python)
![Hyperledger Indy](https://img.shields.io/badge/Hyperledger-Indy-orange?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-ARM64%20Native-2496ED?style=flat-square&logo=docker)
![Architecture](https://img.shields.io/badge/Architecture-SSI%20%2F%20DID%20%2F%20VC%20%2F%20VP-green?style=flat-square)

Hyperledger Indy 블록체인 네트워크(`von-network`)를 활용하여 **자기주권신원(Self-Sovereign Identity, SSI)**의 핵심인 **DID(탈중앙 식별자)** 생성, **VC(검증 가능한 자격증명)** 발급, 그리고 **VP(검증 가능한 프레젠테이션)** 영지식 증명(ZKP) 검증 라이프사이클을 구현한 프로젝트입니다.

---

## 프로젝트 핵심 요소

1. **온체인 신뢰 앵커(Trust Anchor) 등록 및 트랜잭션 검증**
   - 네트워크 최고 관리자(Steward) 권한을 활용하여 Issuer(발급자) DID를 원장에 등록
   - 자격증명 구조 정의서인 **Schema** 및 **Credential Definition (CredDef)** 블록체인 상에 영구 기록
2. **개인정보 보호 중심의 VC 발급**
   - Holder(소유자)의 고유 비밀값(Master Secret) 결합을 통해 타인에 의한 명의 도용 차단
   - 암호화된 로컬 지갑(Wallet)에 자격증명 수령 및 보관
3. **영지식 증명(ZKP) 기반 VP 검증**
   - Verifier(검증자)의 Proof Request 조건에 맞는 최소 정보만 선택적으로 공개(Selective Disclosure)
   - 원본 VC나 개인키 노출 없이 블록체인의 온체인 공개키 정보를 통한 암호학적 서명 검증 수행

---

##  시스템 아키텍처 & 라이프사이클 흐름

```mermaid
sequenceDiagram
    autonumber
    actor Issuer as 발급자 (Issuer / 대학교)
    actor Holder as 소유자 (Holder / 학생)
    actor Verifier as 검증자 (Verifier / 기업)
    participant Ledger as 블록체인 원장 (von-network)

    Note over Issuer, Ledger: [Step 1] 스키마 & CredDef 온체인 등록 (1_issuer_schema_cred_def.py)
    Issuer->>Ledger: Steward 권한으로 Issuer DID (Trust Anchor) 등록
    Issuer->>Ledger: 학위 정보 Schema (DegreeSchema) 등록
    Issuer->>Ledger: 암호키 포함 Credential Definition (CredDef) 등록

    Note over Issuer, Holder: [Step 2] VC 자격증명 발급 & 지갑 저장 (2_issue_credential.py)
    Issuer->>Holder: Credential Offer (발급 제안) 전송
    Holder->>Issuer: Master Secret 결합 Credential Request (발급 요청) 전송
    Issuer->>Holder: 암호화 서명된 VC (Verifiable Credential) 발급
    Holder->>Holder: 암호화 로컬 지갑(test-wallet)에 VC 보관

    Note over Holder, Verifier: [Step 3] VP 제출 및 온체인 암호학적 검증 (3_verify_presentation.py)
    Verifier->>Holder: Proof Request (필수 검증 속성: 이름, 전공) 전달
    Holder->>Holder: 지갑 내 VC에서 필요한 데이터만 추출하여 VP(Proof) 생성
    Holder->>Verifier: 영지식 증명 기반 VP (Verifiable Presentation) 제출
    Verifier->>Ledger: 온체인 Schema & CredDef 공개키 조회
    Verifier->>Verifier: VP 서명 수학적 검증 (Result: True)
```

---

##  기술 스택 (Tech Stack)

| 구분 | 사용 기술 |
|---|---|
| **Ledger Network** | Hyperledger Indy, `von-network` (4 Node BFT Consensus) |
| **SDK & Core** | Python 3, `python3-indy`, `indy-vdr` |
| **Crypto & Storage** | Zero-Knowledge Proof (ZKP), Libsodium, RocksDB |
| **Container & OS** | Docker Desktop, Apple Silicon (M2 ARM64 Native Containerization) |

---

##  트러블슈팅 및 환경 최적화 (Problem Solving)

> **Apple Silicon (M2 Mac) x86_64 에뮬레이션 블록킹 문제 해결**
> - **문제 상황**: 기존 x86_64 기반 `bcgov/von-image` 실행 시, QEMU/Rosetta 에뮬레이션 환경에서 Indy Plenum consensus 이벤트 루프가 교착 상태(Freeze)에 빠져 노드 간 통신이 중단되는 문제 발생.
> - **원인 분석**: C/Python 저수준 `epoll` 및 ZMQ 소켓 통신 시 64비트 메세지 시그널이 x86_64 에뮬레이터 레이어에서 드랍됨을 규명.
> - **해결 방안**: Dockerfile 베이스 이미지를 Apple Silicon 네이티브 `snel/von-image:node-1.12-4-arm64`로 교체하고, `indy_vdr~=0.4.0` arm64 휠 의존성을 재구성하여 에뮬레이션 레이어 없이 **M2 칩셋에서 ARM64 네이티브로 100% 구동**되도록 최적화 완료.

---

##  실행 가이드 (Quick Start)

### 사전 조건 (Prerequisites)
- Docker Desktop 실행 (`von-network` 가 구동 중이어야 함)

### 1단계: 저장소 클론
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

### 2단계: 실습 파이프라인 단계를 순서대로 실행
```bash
# Step 1: Issuer Schema 및 CredDef 원장 등록
./run.sh 1

# Step 2: Holder VC 발급 및 암호화 지갑 저장
./run.sh 2

# Step 3: Verifier VP 제출 및 온체인 영지식 검증
./run.sh 3
```

---

##  파일 구조 (Directory Structure)

```text
├── 1_issuer_schema_cred_def.py   # Step 1: 스키마 및 CredDef 온체인 등록 스크립트
├── 2_issue_credential.py          # Step 2: VC 자격증명 발급 및 지갑 저장 스크립트
├── 3_verify_presentation.py       # Step 3: VP 제출 및 영지식 증명 검증 스크립트
├── pool_transactions_genesis      # 로컬 노드 연결 제네시스 트랜잭션 파일
├── run.sh                         # 도커 컨테이너 기반 실습 통합 실행 파이프라인
└── .idea/runConfigurations/       # 파이Charm원클릭 실행 구성 설정을 위한 메타데이터
```
