import logging
import sys

# 로깅 설정 함수
def setup_logger(name: str = 'logger') -> logging.Logger:
    """
    주어진 이름으로 로거를 생성하고 설정합니다.
    
    Args:
        name (str): logger 이름
        
    Returns:
        logging.Logger: 설정된 로거 객체
    """
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)  # 로그 레벨 설정

    # 핸들러 설정 (stdout에 로그를 출력)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    # 로그 포맷 설정
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # 핸들러를 로거에 추가
    if not logger.handlers:  # 중복 핸들러 추가 방지
        logger.addHandler(handler)

    return logger
