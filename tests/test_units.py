"""
單一法定土地面積換算常數測試 (Exact conversion verification)
依據規範：
1 坪 = 3.305785 平方公尺 (PING_TO_SQM)
內部一律以全精度運算，嚴禁擅自簡化成 3.3 或 3.3058
"""

import pytest
from twintower.constants import PING_TO_SQM, SQM_TO_PING


def test_ping_to_sqm_exact_constant():
    # 法定嚴格常數檢驗
    assert PING_TO_SQM == 3.305785
    assert abs(SQM_TO_PING - (1.0 / 3.305785)) < 1e-12


def test_conversion_reversibility():
    # 測試換算之可逆性與精度
    ping_values = [1.0, 7.0, 5.5, 10.0, 25.43, 100.0]
    for p in ping_values:
        sqm = p * PING_TO_SQM
        p_recalc = sqm * SQM_TO_PING
        assert pytest.approx(p, rel=1e-10) == p_recalc


def test_sqm_to_ping_thresholds():
    # 方案 B 核心門檻：土地 >= 7 坪 (約 23.140495 m²)
    # 接近門檻：土地 >= 5.5 坪 (約 18.1818175 m²)
    core_sqm = 7.0 * PING_TO_SQM
    near_sqm = 5.5 * PING_TO_SQM

    assert pytest.approx(core_sqm, abs=1e-5) == 23.140495
    assert pytest.approx(near_sqm, abs=1e-5) == 18.1818175
