"""
Tests for SEC collector: director extraction layouts and filing pagination.

Uses small synthetic HTML modelled on real DEF 14A layouts (name above the
"Director since" marker, name below it, ALLCAPS names with trailing ages,
and Apple-style "Election of Directors:" lists).
"""

import pytest

from data.sec_collector import SECCollector


@pytest.fixture
def collector(tmp_path):
    return SECCollector(cache_dir=tmp_path)


def _doc(body: str) -> str:
    return f"<html><body>{body}</body></html>"


def _table_mentions(*names: str) -> str:
    """Committee-style table repeating each name as a standalone line."""
    return "".join(f"<p>{n}</p>" for n in names)


class TestExtractDirectors:
    def test_name_above_director_since(self, collector):
        html = _doc(
            "<p>Herb Allen</p><p>INDEPENDENT</p>"
            "<p>Age: 55 Director since: 2021</p>"
            "<p>Mr. Allen has served as president of a firm.</p>"
            "<p>Marc Bolland</p><p>Age: 63 Director since: 2015</p>"
            "<p>Mr. Bolland was CEO. Bolland joined in 2015.</p>"
            + _table_mentions("Herb Allen", "Marc Bolland")
        )
        assert collector.extract_directors(html) == {"Herb Allen", "Marc Bolland"}

    def test_name_below_director_since(self, collector):
        html = _doc(
            "<p>Age: 62</p><p>Director Since: 2021</p>"
            "<p>Patrick P. Gelsinger Intel’s Chief Executive Officer</p>"
            "<p>Gelsinger leads Intel. Gelsinger joined in 2021.</p>"
            + _table_mentions("Patrick P. Gelsinger")
        )
        assert collector.extract_directors(html) == {"Patrick Gelsinger"}

    def test_allcaps_name_and_trailing_age(self, collector):
        html = _doc(
            "<p>ARI BOUSBIB</p><p>Director since: 2007</p><p>Age: 62</p>"
            "<p>Mr. Bousbib is chairman. Bousbib started in 2007.</p>"
            "<p>David Solomon, 61</p><p>Chairman and CEO</p>"
            "<p>Director Since: October 2018</p>"
            "<p>Solomon is CEO. Solomon joined in 2018.</p>"
            + _table_mentions("Ari Bousbib")
        )
        assert collector.extract_directors(html) == {"Ari Bousbib", "David Solomon"}

    def test_credentials_and_apostrophes_stripped(self, collector):
        html = _doc(
            "<p>Albert Bourla, DVM, Ph.D.</p><p>Chairman and CEO</p>"
            "<p>Age: 61</p><p>Director Since: 2018</p>"
            "<p>Bourla is CEO. Bourla joined in 2018. Bourla again.</p>"
            "<p>Mary D'Angelo</p><p>Director since 2015</p>"
            "<p>D'Angelo is a director. D'Angelo again.</p>"
            + _table_mentions("Mary D'Angelo")
        )
        assert collector.extract_directors(html) == {"Albert Bourla", "Mary D'Angelo"}

    def test_election_list_includes_ceo_without_card_marker(self, collector):
        html = _doc(
            "<p>Election of Directors: James Bell, Tim Cook, Al Gore and "
            "Sue Wagner FOR each of the nominees</p>"
        )
        assert collector.extract_directors(html) == {
            "James Bell", "Timothy Cook", "Albert Gore", "Susan Wagner"
        }

    def test_organizations_in_bios_are_ignored(self, collector):
        html = _doc(
            "<p>Ana Botin</p><p>Director since 2013</p>"
            "<p>Palo Alto Networks</p><p>Lockheed Martin</p>"
            "<p>Botin chairs the bank. Botin joined in 2013. Botin again.</p>"
            + _table_mentions("Ana Botin")
        )
        result = collector.extract_directors(html)
        assert result == {"Ana Botin"}

    def test_middle_initials_do_not_split_identity(self, collector):
        html = _doc(
            "<p>Timothy P. Flynn</p><p>Director since 2012</p>"
            "<p>Flynn was CEO. Flynn again. Flynn joined.</p>"
            + _table_mentions("Timothy P. Flynn")
        )
        assert collector.extract_directors(html) == {"Timothy Flynn"}

    def test_initial_first_name_uses_given_name(self, collector):
        html = _doc(
            "<p>L. John Doerr</p><p>Director since 2004</p>"
            "<p>Doerr is a VC. Doerr again. Doerr joined.</p>"
            + _table_mentions("L. John Doerr")
        )
        assert collector.extract_directors(html) == {"John Doerr"}

    def test_no_markers_returns_empty(self, collector):
        assert collector.extract_directors(_doc("<p>Nothing relevant.</p>")) == set()


class TestFindProxyFilings:
    def _collector_with(self, tmp_path, monkeypatch, recent, archives):
        collector = SECCollector(cache_dir=tmp_path)

        def fake_filings(cik):
            return {
                "filings": {
                    "recent": recent,
                    "files": [
                        {"name": name, "filingFrom": lo, "filingTo": hi}
                        for name, (lo, hi, _) in archives.items()
                    ],
                }
            }

        class _Resp:
            def __init__(self, payload):
                self._payload = payload

            def json(self):
                return self._payload

        fetched = []

        def fake_request(url):
            name = url.rsplit("/", 1)[-1]
            fetched.append(name)
            return _Resp(archives[name][2])

        monkeypatch.setattr(collector, "get_company_filings", fake_filings)
        monkeypatch.setattr(collector, "_make_request", fake_request)
        return collector, fetched

    @staticmethod
    def _block(form, date, acc):
        return {
            "form": [form], "filingDate": [date],
            "accessionNumber": [acc], "primaryDocument": [f"{acc}.htm"],
        }

    def test_older_filings_found_in_archive_pages(self, tmp_path, monkeypatch):
        recent = self._block("8-K", "2025-10-01", "recent-1")
        archives = {
            "CIK1-submissions-001.json": (
                "2022-01-01", "2024-12-31",
                self._block("DEF 14A", "2023-04-04", "proxy-2023"),
            ),
            "CIK1-submissions-002.json": (
                "2010-01-01", "2021-12-31",
                self._block("DEF 14A", "2019-04-04", "proxy-2019"),
            ),
        }
        collector, fetched = self._collector_with(
            tmp_path, monkeypatch, recent, archives)

        filings = collector.find_proxy_filings("0000000001", 2023)

        assert [f["accession_number"] for f in filings] == ["proxy-2023"]
        # Only the archive page whose date range covers 2023 is fetched
        assert fetched == ["CIK1-submissions-001.json"]

    def test_recent_block_still_used(self, tmp_path, monkeypatch):
        recent = self._block("DEF 14A", "2024-04-04", "proxy-2024")
        collector, fetched = self._collector_with(
            tmp_path, monkeypatch, recent, {})

        filings = collector.find_proxy_filings("0000000001", 2024)

        assert [f["accession_number"] for f in filings] == ["proxy-2024"]
        assert fetched == []


class TestCollectBoardData:
    def _collector(self, tmp_path, monkeypatch, filings):
        collector = SECCollector(cache_dir=tmp_path)
        collector.ticker_to_cik_map = {"ABC": "0000000001"}
        monkeypatch.setattr(collector, "load_ticker_to_cik_map", lambda *a, **k: {})
        monkeypatch.setattr(collector, "find_proxy_filings", lambda cik, year: filings)
        downloaded = []

        def fake_download(cik, accession_number, document):
            downloaded.append(accession_number)
            return _doc(
                "<p>Herb Allen</p><p>Director since: 2021</p>"
                "<p>Allen is a director. Allen again. Allen joined.</p>"
                + _table_mentions("Herb Allen")
            )

        monkeypatch.setattr(collector, "download_filing", fake_download)
        return collector, downloaded

    @staticmethod
    def _filing(form, acc):
        return {"form": form, "filing_date": "2023-04-01",
                "accession_number": acc, "primary_document": f"{acc}.htm",
                "cik": "0000000001"}

    def test_defa14a_only_is_skipped(self, tmp_path, monkeypatch, capsys):
        collector, downloaded = self._collector(
            tmp_path, monkeypatch, [self._filing("DEFA14A", "supp-1")])

        df = collector.collect_board_data(["ABC"], 2023, verbose=True)

        assert df.empty
        assert downloaded == []
        assert "No DEF 14A" in capsys.readouterr().out

    def test_def14a_preferred_over_defa14a(self, tmp_path, monkeypatch):
        collector, downloaded = self._collector(
            tmp_path, monkeypatch,
            [self._filing("DEFA14A", "supp-1"), self._filing("DEF 14A", "proxy-1")])

        df = collector.collect_board_data(["ABC"], 2023, verbose=False)

        assert downloaded == ["proxy-1"]
        assert list(df["director_name"]) == ["Herb Allen"]
