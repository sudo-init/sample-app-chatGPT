FROM node:20-alpine

# 작업 디렉토리 설정
WORKDIR /home/node/app

# 패키지 파일 복사 및 의존성 설치
COPY ./frontend/package*.json ./
RUN npm install

# 소스 코드 복사
COPY . .

# 작업 디렉토리 설정
WORKDIR /home/node/app/frontend

# 애플리케이션 시작 (빌드 단계는 제거됨)
CMD ["npm", "run", "dev"]
