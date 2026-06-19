import pytest
from PIL import Image
from app.services.image_tiler import needs_tiling, split_into_tiles, MAX_TILES

@pytest.mark.tiling
@pytest.mark.smoke
def test_needs_tiling():
    """타일링 필요 여부 판단 테스트"""
    # 2:3 비율 (정상) -> 1200 / 800 = 1.5 < 2.5
    assert not needs_tiling(800, 1200)
    
    # 1:3 비율 (세로로 긴) -> 2400 / 800 = 3.0 >= 2.5
    assert needs_tiling(800, 2400)

@pytest.mark.tiling
@pytest.mark.full
def test_split_into_tiles():
    """세로 긴 이미지 타일 분할 테스트"""
    img = Image.new("RGB", (800, 3000), color="white")
    
    # 높이 3000, TILE_HEIGHT=1200, OVERLAP=200, stride=1000
    # 타일1: 0~1200
    # 타일2: 1000~2200
    # 타일3: 2000~3000
    # 총 3장 나와야 함
    tiles = split_into_tiles(img)
    assert len(tiles) == 3
    assert all(t.startswith("data:image/jpeg;base64,") for t in tiles)

@pytest.mark.tiling
@pytest.mark.full
def test_split_into_tiles_max_limit():
    """초고해상도 이미지 타일 분할 시 MAX_TILES 제한 확인"""
    img = Image.new("RGB", (800, 10000), color="white")
    tiles = split_into_tiles(img)
    
    assert len(tiles) == MAX_TILES
