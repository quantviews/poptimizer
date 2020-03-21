import pandas as pd
import pytest
import torch

from poptimizer.data import div
from poptimizer.dl import data_params
from poptimizer.dl.features import dividends
from poptimizer.dl.features.feature import FeatureTypes

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "forecast_days": 4,
    "features": {
        "Label": {"div_share": 0.9},
        "Prices": {},
        "Dividends": {},
        "Weight": {},
    },
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_start_date = div.STATS_START
    div.STATS_START = pd.Timestamp("2010-09-01")

    params = data_params.ValParams(
        ("CNTLP", "LKOH"), pd.Timestamp("2020-03-18"), PARAMS
    )
    yield dividends.Dividends("CNTLP", params)

    div.STATS_START = saved_start_date


class TestLabel:
    def test_getitem(self, feature):
        assert feature[0].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[0][0])
        assert torch.tensor(0.0).allclose(feature[0][5])
        assert torch.tensor(0.0).allclose(feature[0][7])

        assert feature[53].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[53][0])
        assert torch.tensor(0.0).allclose(feature[53][4])
        assert torch.tensor(0.296263787).allclose(feature[53][5])
        assert torch.tensor(0.296263787).allclose(feature[53][7])

        assert feature[236].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[236][0])
        assert torch.tensor(0.0).allclose(feature[236][4])
        assert torch.tensor(0.0).allclose(feature[236][7])

    def test_name(self, feature):
        assert feature.name == "Dividends"

    def test_type(self, feature):
        assert feature.type is FeatureTypes.NUMERICAL