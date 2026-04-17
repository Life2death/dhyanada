"""Tests for intent classifier — Marathi, English, and transliteration scenarios."""
import pytest

from src.router.intent import classify, _regex_classify, _extract_entity, CROP_MAP, DISTRICT_MAP


# ---------------------------------------------------------------------------
# Synchronous regex unit tests (no I/O)
# ---------------------------------------------------------------------------

class TestGreetings:
    def test_namaskar_marathi(self):
        assert _regex_classify("नमस्कार") == "greeting"

    def test_hello_marathi(self):
        assert _regex_classify("हॅलो") == "greeting"

    def test_hi_english(self):
        assert _regex_classify("hi") == "greeting"

    def test_hello_english(self):
        assert _regex_classify("hello") == "greeting"

    def test_namaskar_case_insensitive(self):
        assert _regex_classify("NAMASKAR") == "greeting"

    def test_greeting_with_extra_space_does_not_match(self):
        # "hi there" should NOT be a greeting (not exact match)
        result = _regex_classify("hi there")
        assert result != "greeting"


class TestPriceQueries:
    """Price queries in Marathi, transliteration, and English."""

    def test_soyabean_bhav_marathi(self):
        assert _regex_classify("सोयाबीन भाव") == "price_query"

    def test_tur_dar_marathi(self):
        assert _regex_classify("तूर दर") == "price_query"

    def test_kapus_bhaav_marathi(self):
        assert _regex_classify("कापूस भाव") == "price_query"

    def test_soyabean_rate_english(self):
        assert _regex_classify("soyabean rate") == "price_query"

    def test_cotton_price_english(self):
        assert _regex_classify("cotton price") == "price_query"

    def test_tur_bhav_transliteration(self):
        assert _regex_classify("tur bhav") == "price_query"

    def test_soybin_dar_transliteration(self):
        assert _regex_classify("soybin dar") == "price_query"

    def test_kapus_price_transliteration(self):
        assert _regex_classify("kapus price") == "price_query"

    def test_toor_bhaav_transliteration(self):
        assert _regex_classify("toor bhaav") == "price_query"

    def test_soyabean_with_district_marathi(self):
        assert _regex_classify("लातूर सोयाबीन भाव") == "price_query"

    def test_kapas_rate_transliteration(self):
        assert _regex_classify("kapas rate") == "price_query"

    def test_crop_only_no_price_word(self):
        # "सोयाबीन" alone still matches price_query (crop name implies price intent)
        assert _regex_classify("सोयाबीन") == "price_query"

    def test_price_word_only_no_crop(self):
        # "भाव" alone — price word without crop still matches
        assert _regex_classify("भाव") == "price_query"


class TestHelp:
    def test_madat_marathi(self):
        assert _regex_classify("मदत") == "help"

    def test_menu_english(self):
        assert _regex_classify("menu") == "help"

    def test_menu_marathi(self):
        assert _regex_classify("मेनू") == "help"

    def test_help_english(self):
        assert _regex_classify("help") == "help"


class TestStop:
    def test_stop_english(self):
        assert _regex_classify("stop") == "stop"

    def test_thamba_marathi(self):
        assert _regex_classify("थांबा") == "stop"

    def test_band_marathi(self):
        assert _regex_classify("बंद") == "stop"

    def test_stop_uppercase(self):
        assert _regex_classify("STOP") == "stop"


class TestDelete:
    def test_delete_english(self):
        assert _regex_classify("delete") == "delete"

    def test_delete_marathi(self):
        assert _regex_classify("माझा डेटा हटवा") == "delete"

    def test_erase_english(self):
        assert _regex_classify("erase") == "delete"

    def test_delete_my_data_english(self):
        assert _regex_classify("delete my data") == "delete"


class TestSubscribe:
    def test_upgrade_english(self):
        assert _regex_classify("upgrade") == "subscribe"

    def test_subscribe_english(self):
        assert _regex_classify("subscribe") == "subscribe"

    def test_sadasyata_marathi(self):
        assert _regex_classify("सदस्यता") == "subscribe"

    def test_paid_english(self):
        assert _regex_classify("paid") == "subscribe"

    def test_premium_english(self):
        assert _regex_classify("premium") == "subscribe"


class TestUnknown:
    def test_random_marathi(self):
        # Unrelated Marathi text should not match any rule
        result = _regex_classify("आज हवामान कसे आहे")
        assert result is None

    def test_random_english(self):
        result = _regex_classify("what is the weather today")
        assert result is None


# ---------------------------------------------------------------------------
# Entity extraction tests
# ---------------------------------------------------------------------------

class TestCropExtraction:
    def test_soyabean_marathi(self):
        assert _extract_entity("सोयाबीन भाव", CROP_MAP) == "soyabean"

    def test_tur_marathi(self):
        assert _extract_entity("तूर दर", CROP_MAP) == "tur"

    def test_kapus_marathi(self):
        assert _extract_entity("कापूस", CROP_MAP) == "cotton"

    def test_soyabean_english(self):
        assert _extract_entity("soyabean price", CROP_MAP) == "soyabean"

    def test_soybean_alternate_spelling(self):
        assert _extract_entity("soybean rate", CROP_MAP) == "soyabean"

    def test_soybin_transliteration(self):
        assert _extract_entity("soybin bhav", CROP_MAP) == "soyabean"

    def test_tur_transliteration(self):
        assert _extract_entity("tur bhav", CROP_MAP) == "tur"

    def test_toor_transliteration(self):
        assert _extract_entity("toor price", CROP_MAP) == "tur"

    def test_tuur_transliteration(self):
        assert _extract_entity("tuur dar", CROP_MAP) == "tur"

    def test_cotton_english(self):
        assert _extract_entity("cotton price", CROP_MAP) == "cotton"

    def test_kapus_transliteration(self):
        assert _extract_entity("kapus rate", CROP_MAP) == "cotton"

    def test_kapas_transliteration(self):
        assert _extract_entity("kapas bhav", CROP_MAP) == "cotton"

    def test_kaapus_transliteration(self):
        assert _extract_entity("kaapus price", CROP_MAP) == "cotton"

    def test_no_crop_returns_none(self):
        assert _extract_entity("आज हवामान चांगले आहे", CROP_MAP) is None


class TestDistrictExtraction:
    def test_latur_marathi(self):
        assert _extract_entity("लातूर", DISTRICT_MAP) == "latur"

    def test_nanded_marathi(self):
        assert _extract_entity("नांदेड", DISTRICT_MAP) == "nanded"

    def test_jalna_marathi(self):
        assert _extract_entity("जालना", DISTRICT_MAP) == "jalna"

    def test_akola_marathi(self):
        assert _extract_entity("अकोला", DISTRICT_MAP) == "akola"

    def test_yavatmal_marathi(self):
        assert _extract_entity("यवतमाळ", DISTRICT_MAP) == "yavatmal"

    def test_latur_english(self):
        assert _extract_entity("latur soyabean", DISTRICT_MAP) == "latur"

    def test_nanded_english(self):
        assert _extract_entity("nanded cotton price", DISTRICT_MAP) == "nanded"

    def test_yavatmal_alternate(self):
        assert _extract_entity("yawatmal tur", DISTRICT_MAP) == "yavatmal"

    def test_nandad_alternate(self):
        assert _extract_entity("nandad rate", DISTRICT_MAP) == "nanded"

    def test_no_district_returns_none(self):
        assert _extract_entity("सोयाबीन भाव", DISTRICT_MAP) is None


# ---------------------------------------------------------------------------
# Async classify() integration (regex path — no LLM call needed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_classify_soyabean_latur_marathi():
    result = await classify("लातूर सोयाबीन भाव")
    assert result.intent == "price_query"
    assert result.crop == "soyabean"
    assert result.district == "latur"
    assert result.confidence == "regex"


@pytest.mark.asyncio
async def test_classify_tur_nanded():
    result = await classify("नांदेड तूर दर")
    assert result.intent == "price_query"
    assert result.crop == "tur"
    assert result.district == "nanded"


@pytest.mark.asyncio
async def test_classify_cotton_yavatmal_transliteration():
    result = await classify("yavatmal kapus price")
    assert result.intent == "price_query"
    assert result.crop == "cotton"
    assert result.district == "yavatmal"


@pytest.mark.asyncio
async def test_classify_greeting_namaskar():
    result = await classify("नमस्कार")
    assert result.intent == "greeting"
    assert result.confidence == "regex"


@pytest.mark.asyncio
async def test_classify_stop_marathi():
    result = await classify("थांबा")
    assert result.intent == "stop"


@pytest.mark.asyncio
async def test_classify_delete_marathi():
    result = await classify("माझा डेटा हटवा")
    assert result.intent == "delete"


@pytest.mark.asyncio
async def test_classify_help_marathi():
    result = await classify("मदत")
    assert result.intent == "help"


@pytest.mark.asyncio
async def test_classify_jalna_tur_mixed():
    result = await classify("jalna तूर bhav")
    assert result.intent == "price_query"
    assert result.crop == "tur"
    assert result.district == "jalna"


@pytest.mark.asyncio
async def test_classify_akola_soyabean():
    result = await classify("अकोला soyabean rate")
    assert result.intent == "price_query"
    assert result.crop == "soyabean"
    assert result.district == "akola"
