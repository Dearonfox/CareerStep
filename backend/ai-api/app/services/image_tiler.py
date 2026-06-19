import io
import base64
import aiohttp
from PIL import Image

ASPECT_RATIO_THRESHOLD = 2.5  # 세로/가로 비율이 이 값 이상이면 타일링
TILE_HEIGHT = 1200             # 각 타일의 목표 높이 (px)
OVERLAP = 200                  # 타일 간 겹침 영역 (px)
MAX_TILES = 6                  # 최대 타일 수 (API 비용 제한)

async def fetch_image(url: str) -> Image.Image:
    """URL에서 이미지를 다운로드하여 PIL Image로 반환"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.read()
            return Image.open(io.BytesIO(data))

def needs_tiling(width: int, height: int) -> bool:
    """타일링이 필요한지 판단"""
    if width == 0:
        return False
    return (height / width) >= ASPECT_RATIO_THRESHOLD

def split_into_tiles(img: Image.Image) -> list[str]:
    """이미지를 타일로 분할하고 base64 데이터 URL 목록으로 반환"""
    width, height = img.size
    
    if not needs_tiling(width, height):
        # 타일링 불필요 → 원본 1장 반환
        return [image_to_data_url(img)]
    
    tiles = []
    y = 0
    stride = TILE_HEIGHT - OVERLAP
    
    while y < height and len(tiles) < MAX_TILES:
        y_end = min(y + TILE_HEIGHT, height)
        tile = img.crop((0, y, width, y_end))
        tiles.append(image_to_data_url(tile))
        
        if y_end >= height:
            break
        y += stride
    
    return tiles

def image_to_data_url(img: Image.Image) -> str:
    """PIL Image → base64 data URL"""
    buffer = io.BytesIO()
    # RGB 변환 (png 처럼 투명도 있는 경우 JPEG 저장 오류 방지)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(buffer, format="JPEG", quality=85)
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"

async def prepare_image_inputs(image_urls: list[str]) -> list[str]:
    """
    이미지 URL 목록을 받아, 필요시 타일링하여 Vision API에 전달할 
    이미지 URL/data URL 목록을 반환합니다.
    """
    result = []
    for url in image_urls:
        try:
            img = await fetch_image(url)
            tiles = split_into_tiles(img)
            result.extend(tiles)
        except Exception as e:
            # 다운로드 실패 시 원본 URL 그대로 전달 (API가 직접 fetch)
            result.append(url)
    
    return result[:MAX_TILES]  # 최대 타일 수 제한
