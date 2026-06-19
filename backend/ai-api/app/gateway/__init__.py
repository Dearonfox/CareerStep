from app.gateway.client import GPTGateway

# AI API 백엔드 전체에서 공유될 단일 GPT Gateway 인스턴스
gpt_gateway = GPTGateway()

__all__ = ["gpt_gateway"]
