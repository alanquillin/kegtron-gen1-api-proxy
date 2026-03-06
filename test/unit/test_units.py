import pytest
from lib.units import from_ml, to_ml


class TestFromML:
    def test_from_ml_with_none_value(self):
        assert from_ml(None, "ml") is None
        assert from_ml(None, "l") is None
        
    def test_from_ml_with_zero_value(self):
        assert from_ml(0, "ml") == 0
        assert from_ml(0, "l") == 0
        
    def test_from_ml_to_ml(self):
        assert from_ml(1000, "ml") == 1000
        
    def test_from_ml_to_liters(self):
        assert from_ml(1000, "l") == 1.0
        assert from_ml(2500, "l") == 2.5
        
    def test_from_ml_to_gallons(self):
        assert from_ml(1000, "gal") == pytest.approx(0.2641721)
        assert from_ml(3785.41, "gal") == pytest.approx(1.0, rel=1e-3)
        
    def test_from_ml_to_imperial_gallons(self):
        assert from_ml(1000, "gal (imperial)") == pytest.approx(0.219969, rel=1e-5)
        
    def test_from_ml_to_pints(self):
        assert from_ml(1000, "pt") == pytest.approx(2.1133764)
        
    def test_from_ml_to_imperial_pints(self):
        assert from_ml(1000, "p (imperial)") == pytest.approx(1.75975)
        
    def test_from_ml_to_quarts(self):
        assert from_ml(1000, "qt") == pytest.approx(1.0566882)
        
    def test_from_ml_to_imperial_quarts(self):
        assert from_ml(1000, "qt (imperial)") == pytest.approx(0.879877, rel=1e-5)
        
    def test_from_ml_to_cups(self):
        assert from_ml(1000, "cup") == pytest.approx(4.2267528)
        
    def test_from_ml_to_imperial_cups(self):
        assert from_ml(1000, "cup (imperial)") == pytest.approx(3.51951, rel=1e-5)
        
    def test_from_ml_to_oz(self):
        assert from_ml(1000, "oz") == pytest.approx(33.814)
        
    def test_from_ml_to_imperial_oz(self):
        assert from_ml(1000, "oz (imperial)") == pytest.approx(35.1951, rel=1e-4)
        
    def test_from_ml_invalid_unit(self):
        with pytest.raises(Exception, match="invalid volume unit for conversion"):
            from_ml(1000, "invalid")
            
    def test_from_ml_case_insensitive(self):
        assert from_ml(1000, "ML") == 1000
        assert from_ml(1000, "L") == 1.0
        assert from_ml(1000, "GAL") == pytest.approx(0.2641721)


class TestToML:
    def test_to_ml_with_none_value(self):
        assert to_ml(None, "ml") is None
        assert to_ml(None, "l") is None
        
    def test_to_ml_with_zero_value(self):
        assert to_ml(0, "ml") == 0
        assert to_ml(0, "l") == 0
        
    def test_to_ml_from_ml(self):
        assert to_ml(1000, "ml") == 1000
        
    def test_to_ml_from_liters(self):
        assert to_ml(1.0, "l") == 1000
        assert to_ml(2.5, "l") == 2500
        
    def test_to_ml_from_gallons(self):
        assert to_ml(1.0, "gal") == pytest.approx(3785.41, rel=1e-2)
        assert to_ml(0.2641721, "gal") == pytest.approx(1000, rel=1e-3)
        
    def test_to_ml_from_imperial_gallons(self):
        assert to_ml(0.219969, "gal (imperial)") == pytest.approx(1000, rel=1e-3)
        
    def test_to_ml_from_pints(self):
        assert to_ml(2.1133764, "pt") == pytest.approx(1000, rel=1e-3)
        
    def test_to_ml_from_imperial_pints(self):
        assert to_ml(1.75975, "p (imperial)") == pytest.approx(1000, rel=1e-3)
        
    def test_to_ml_from_quarts(self):
        assert to_ml(1.0566882, "qt") == pytest.approx(1000, rel=1e-3)
        
    def test_to_ml_from_imperial_quarts(self):
        assert to_ml(0.879877, "qt (imperial)") == pytest.approx(1000, rel=1e-3)
        
    def test_to_ml_from_cups(self):
        assert to_ml(4.2267528, "cup") == pytest.approx(1000, rel=1e-3)
        
    def test_to_ml_from_imperial_cups(self):
        assert to_ml(3.51951, "cup (imperial)") == pytest.approx(1000, rel=1e-3)
        
    def test_to_ml_from_oz(self):
        assert to_ml(33.814, "oz") == pytest.approx(1000, rel=1e-3)
        
    def test_to_ml_from_imperial_oz(self):
        assert to_ml(35.1951, "oz (imperial)") == pytest.approx(1000, rel=1e-3)
        
    def test_to_ml_invalid_unit(self):
        with pytest.raises(Exception, match="invalid volume unit for conversion"):
            to_ml(1000, "invalid")
            
    def test_to_ml_case_insensitive(self):
        assert to_ml(1000, "ML") == 1000
        assert to_ml(1.0, "L") == 1000
        assert to_ml(1.0, "GAL") == pytest.approx(3785.41, rel=1e-2)


class TestRoundTripConversions:
    def test_round_trip_conversions(self):
        original_ml = 1000.0
        units = ["ml", "l", "gal", "gal (imperial)", "pt", "p (imperial)", 
                  "qt", "qt (imperial)", "cup", "cup (imperial)", "oz", "oz (imperial)"]
        
        for unit in units:
            converted = from_ml(original_ml, unit)
            back_to_ml = to_ml(converted, unit)
            assert back_to_ml == pytest.approx(original_ml, rel=1e-6)