#!/bin/bash

# 한글 출력을 위한 인코딩 설정
export LANG=ko_KR.UTF-8

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로고 출력
echo -e "${GREEN}"
echo "============================================="
echo "     NICE Guidance 크롤러 실행 스크립트     "
echo "============================================="
echo -e "${NC}"

# 메인 메뉴 함수
show_menu() {
    echo -e "\n다음 중 선택해주세요:"
    echo "1) 전체 수집"
    echo "2) 조건 설정"
    echo "3) 종료"
    read -p "선택 (1-3): " choice
    return $choice
}

# 환경 변수 설정 함수
set_environment_variables() {
    # LOG_LEVEL 설정
    echo -e "\n${YELLOW}[LOG_LEVEL 설정]${NC}"
    echo "로그 레벨을 설정합니다. (DEBUG, INFO, WARNING, ERROR)"
    echo "기본값: INFO"
    read -p "LOG_LEVEL을 입력하세요 (Enter 시 기본값): " LOG_LEVEL
    LOG_LEVEL=${LOG_LEVEL:-INFO}

    # SEARCH_QUERY 설정
    echo -e "\n${YELLOW}[검색어 설정]${NC}"
    echo "검색할 키워드를 입력합니다."
    echo "기본값: 없음"
    read -p "검색어를 입력하세요 (Enter 시 기본값): " SEARCH_QUERY

    # FROM_DATE 설정
    echo -e "\n${YELLOW}[시작 날짜 설정]${NC}"
    echo "검색 시작 날짜를 설정합니다. (형식: YYYY-MM-DD)"
    echo "기본값: 2000-01-01 (처음)"
    read -p "시작 날짜를 입력하세요 (Enter 시 2000-01-01): " FROM_DATE
    FROM_DATE=${FROM_DATE:-$(date +%Y-%m-%d)}

    # TO_DATE 설정
    echo -e "\n${YELLOW}[종료 날짜 설정]${NC}"
    echo "검색 종료 날짜를 설정합니다. (형식: YYYY-MM-DD)"
    echo "기본값: 오늘"
    read -p "종료 날짜를 입력하세요 (Enter 시 오늘): " TO_DATE
    TO_DATE=${TO_DATE:-$(date +%Y-%m-%d)}

    # TYPE 설정
    echo -e "\n${YELLOW}[Type 설정]${NC}"
    echo "Type을 설정합니다. (Guidance, NICE advice, Quality standard)"
    echo "기본값: 없음"
    read -p "Type을 입력하세요 (Enter 시 기본값): " TYPE
    TYPE=${TYPE:-""}

    # Guidance Programme 설정
    echo -e "\n${YELLOW}[Guidance Programme 설정]${NC}"
    echo "Guidance Programme을 설정합니다."
    echo "기본값: 없음"
    read -p "Guidance Programme을 입력하세요 (Enter 시 기본값): " GUIDANCE_PROGRAMME
    GUIDANCE_PROGRAMME=${GUIDANCE_PROGRAMME:-""}
}

# Docker 실행 명령어 생성 함수
generate_docker_command() {
    local cmd="docker run -v \$(pwd)/output:/app/output -v \$(pwd)/logs:/app/logs"
    
    # 환경 변수 추가
    [[ ! -z "$LOG_LEVEL" ]] && cmd+=" -e LOG_LEVEL=$LOG_LEVEL"
    [[ ! -z "$SEARCH_QUERY" ]] && cmd+=" -e SEARCH_QUERY=\"$SEARCH_QUERY\""
    [[ ! -z "$FROM_DATE" ]] && cmd+=" -e FROM_DATE=$FROM_DATE"
    [[ ! -z "$TO_DATE" ]] && cmd+=" -e TO_DATE=$TO_DATE"
    [[ ! -z "$TYPE" ]] && cmd+=" -e TYPE=\"$TYPE\""
    [[ ! -z "$GUIDANCE_PROGRAMME" ]] && cmd+=" -e GUIDANCE_PROGRAMME=\"$GUIDANCE_PROGRAMME\""
    
    cmd+=" guidance-crawler"
    echo "$cmd"
}

# 메인 로직
while true; do
    show_menu
    choice=$?
    
    case $choice in
        1)  # 전체 수집
            echo -e "\n${GREEN}전체 수집을 시작합니다...${NC}"
            (cd crawler && docker build -t guidance-crawler . && cd ..) && \
            docker run -v $(pwd)/output:/app/output -v $(pwd)/logs:/app/logs guidance-crawler
            break
            ;;
        2)  # 조건 설정
            echo -e "\n${GREEN}조건을 설정합니다...${NC}"
            set_environment_variables
            
            echo -e "\n${GREEN}Docker 이미지를 빌드합니다...${NC}"
            (cd crawler && docker build -t guidance-crawler . && cd ..) && \
            eval $(generate_docker_command)
            break
            ;;
        3)  # 종료
            echo -e "\n${GREEN}프로그램을 종료합니다.${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${RED}잘못된 선택입니다. 다시 선택해주세요.${NC}"
            ;;
    esac
done

echo -e "\n${GREEN}크롤링이 완료되었습니다.${NC}" 