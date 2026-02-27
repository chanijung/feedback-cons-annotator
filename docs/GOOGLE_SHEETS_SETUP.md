# Google Sheets 설정 가이드 (Human-LLM 저장)

이 앱은 어노테이션 결과를 Google Sheets에 저장합니다. **Human-Human** 결과와 **Human-LLM** 결과는 서로 다른 시트 탭(tab)에 저장됩니다.

---

## 1. 필요한 시트 탭 (Sheets)

| 모드 | 시트 탭 이름 | 기본값 | `secrets.toml` 키 |
|------|--------------|--------|-------------------|
| Human-Human (H-H) | 중복/동의 페어 | `Sheet1` | `SHEET_NAME` |
| Human-LLM (H-L) | Human–LLM consensus 페어 | `HumanLLM` | `SHEET_NAME_HL` |

---

## 2. HumanLLM 탭이 필요한 이유

- **Human-Human** 결과는 기존 시트(예: `Sheet1`)에 저장됩니다.
- **Human-LLM** 결과는 별도 탭에 저장됩니다. 이유:
  1. 컬럼 구조는 같지만 데이터 의미가 다름 (H-H: duplicate pairs, H-L: consensus pairs)
  2. 나중에 분석 시 모드별로 분리해서 사용하기 쉬움
  3. 기존 H-H 시트를 그대로 두고 H-L만 따로 관리 가능

---

## 3. Google Sheets에서 HumanLLM 탭 만들기

1. **스프레드시트 열기**
   - `SPREADSHEET_ID`에 설정한 스프레드시트 URL로 접속
   - 예: `https://docs.google.com/spreadsheets/d/1ED9QuuQWiUjeq8IUyNTigGMJyuy3ffRV2KaHGKOIjoI/edit`

2. **새 시트 탭 추가**
   - 하단 탭 바에서 `+` (새 시트 추가) 클릭
   - 또는 기존 탭 우클릭 → **복제** 또는 **이동/복사**

3. **탭 이름 지정**
   - 새 탭 더블클릭 → `HumanLLM` 입력
   - 또는 사용할 이름을 정한 뒤 `secrets.toml`에 그대로 반영

4. **서비스 계정 공유**
   - 상단 **공유** 버튼 클릭
   - `gcp_service_account`의 `client_email`(예: `streamlit-google-sheet@...iam.gserviceaccount.com`)을 **편집자** 권한으로 추가
   - 이 계정이 없으면 시트 접근·저장이 되지 않습니다.

---

## 4. `secrets.toml` 설정

`.streamlit/secrets.toml` 예시:

```toml
SPREADSHEET_ID = "1ED9QuuQWiUjeq8IUyNTigGMJyuy3ffRV2KaHGKOIjoI"
SHEET_NAME = "Sheet1"        # Human-Human 결과 탭
SHEET_NAME_HL = "HumanLLM"   # Human-LLM 결과 탭 (직접 만든 탭 이름과 일치해야 함)
```

### SHEET_NAME_HL 값 규칙

- **기본값**: 설정하지 않으면 `HumanLLM`을 사용
- **다른 이름 사용**: 탭을 `H-L Consensus` 등으로 만들었다면  
  `SHEET_NAME_HL = "H-L Consensus"` 로 설정
- **탭 이름은 대소문자·공백까지 정확히 일치**해야 함

---

## 5. 각 시트의 데이터 형식

두 탭 모두 아래와 같은 형식입니다:

| A | B | C | D |
|---|---|---|---|
| annotator_name | paper_id | pairs | timestamp |
| chani | 604_2305_10544v1 | [[0,2],[1,3]] | 2025-02-26T12:00:00+00:00 |
| jimin | 1411_LCQ7YTzgRQ | [[0,1],[2,3]] | 2025-02-26T12:05:00+00:00 |

- **Human-Human (`SHEET_NAME`)**: `pairs` = `[[human_i, human_j], ...]` (같은 페이퍼 내 human feedback 쌍)
- **Human-LLM (`SHEET_NAME_HL`)**: `pairs` = `[[human_idx, llm_idx], ...]` (Human anchor 인덱스, LLM feedback 인덱스)

첫 Submit 시 헤더 행이 없으면 자동으로 생성됩니다.

---

## 6. HumanLLM 탭이 없을 때

- **Submit** 시:
  - Human-Human 결과는 정상 저장
  - Human-LLM 결과 저장 실패 → 메시지 예: `(Human-LLM sheet 'HumanLLM' not found or error: ...)`
- **Load** 시:
  - Human-LLM 시트가 없으면 예외는 무시되고 `pairs_hl`은 빈 상태로 로드

---

## 7. Streamlit Cloud 배포 시

대시보드 → **App settings** → **Secrets**에 아래 형식으로 추가:

```
SPREADSHEET_ID = "your_sheet_id"
SHEET_NAME = "Sheet1"
SHEET_NAME_HL = "HumanLLM"

[gcp_service_account]
type = "service_account"
project_id = "..."
...
```

---

## 정리

| 항목 | 확인 사항 |
|------|-----------|
| 1 | Google Sheets에 `HumanLLM` 탭(또는 지정한 이름) 존재 여부 |
| 2 | `secrets.toml`에 `SHEET_NAME_HL`이 있고, 탭 이름과 동일한지 |
| 3 | 서비스 계정 `client_email`이 스프레드시트 **편집자**로 공유되어 있는지 |
