---
name: customize-opencode
description: Use ONLY when the user is editing or creating opencode's own configuration: opencode.json, opencode.jsonc, files under .agents/skills, files under .opencode/, or files under ~/.config/opencode/. Also use when creating or fixing opencode agents, subagents, skills, plugins, MCP servers, or permission rules. Do not use for the user's own application code, or for any project that is not configuring opencode itself.
---

# Customize OpenCode Skill

이 스킬은 OpenCode 환경 설정 및 구성(config)을 지원합니다. OpenCode 설정 파일인 `opencode.json` 또는 `opencode.jsonc` 파일을 작성하거나 수정할 때, 그리고 관련 스킬 및 명령어 설정을 관리할 때 이 스킬을 활성화하여 사용합니다.

## 핵심 설정 파일 구성

OpenCode 설정은 주로 프로젝트 루트의 `opencode.json` 또는 글로벌 디렉토리(`~/.config/opencode/opencode.json`)에서 관리합니다.

### 1. 기본 구조 예시
```json
{
  "models": {
    "default": "gemini-3.5-flash",
    "providers": {
      "gemini": {
        "apiKey": "{env:GEMINI_API_KEY}"
      }
    }
  },
  "skills": {
    "paths": [
      ".agents/skills"
    ]
  },
  "permissions": {
    "allowedTools": ["*"],
    "allowedPaths": ["d:/ABC-RAG"]
  }
}
```

### 2. 중요 주의사항 및 베스트 프랙티스

* **환경 변수 참조**: 설정 파일 내에서 환경 변수를 참조할 때는 `${ENV_VAR}` 형식이 아닌 **`{env:ENV_VAR}`** 구문을 사용해야 합니다.
* **사용자 정의 명령어 (Custom Commands)**:
  * 커스텀 명령어 작성 시 설정 구조에서 이전 버전의 `prompt` 키는 지원 중단(deprecated)되었거나 `ConfigInvalidError`를 유발할 수 있습니다. 대신 반드시 **`template`** 키를 사용해야 합니다.
  * 복잡한 명령어 설정은 `opencode.json` 파일 내에 인라인으로 구현하기보다는, **`.opencode/command/<name>.md`** 또는 **`.agents/rules/`** 경로의 별도 마크다운 파일로 분리하여 관리하는 것이 좋습니다.
* **스킬(Skills) 경로**:
  * 공유 스킬이나 워크스페이스 내 커스텀 스킬 디렉토리는 `skills.paths`에 `.agents/skills`와 같이 상대 경로로 등록합니다.
  * Antigravity 및 OpenCode 환경에서는 표준 디렉토리 구조에 정의된 스킬을 자동으로 감지합니다.

## 제공되는 에이전트 및 서브에이전트 제어
* 서브에이전트 호출 및 권한 체계 설정은 `opencode.json` 내 `agents` 속성을 활용해 프로필 및 시스템 프롬프트 제약 조건을 오버라이드할 수 있습니다.
* MCP(Model Context Protocol) 서버를 추가하고 싶다면 `mcpServers` 설정을 구성해 필요한 도구(Tools)를 AI에 공급하십시오.
