"""
Tests for name standardization module.
"""

import pytest

from network.name_standardizer import NameStandardizer, standardize_name


class TestNameStandardizer:
    """Test cases for NameStandardizer class."""

    def test_basic_name(self):
        """Test standardization of basic name."""
        standardizer = NameStandardizer()
        result = standardizer.standardize("John Smith")
        assert result == "John Smith"

    def test_nickname_expansion(self):
        """Test nickname expansion."""
        standardizer = NameStandardizer()

        # Test male nicknames
        assert standardizer.standardize("Bob Smith") == "Robert Smith"
        assert standardizer.standardize("Bill Jones") == "William Jones"
        assert standardizer.standardize("Jim Brown") == "James Brown"

        # Test female nicknames
        assert standardizer.standardize("Liz Johnson") == "Elizabeth Johnson"
        assert standardizer.standardize("Kate Williams") == "Katherine Williams"

    def test_title_removal(self):
        """Test removal of titles."""
        standardizer = NameStandardizer()

        assert standardizer.standardize("Mr. John Smith") == "John Smith"
        assert standardizer.standardize("Dr. Jane Doe") == "Jane Doe"
        assert standardizer.standardize("Hon. Robert Johnson") == "Robert Johnson"

    def test_suffix_removal(self):
        """Test removal of suffixes."""
        standardizer = NameStandardizer()

        assert standardizer.standardize("John Smith Jr.") == "John Smith"
        assert standardizer.standardize("Robert Jones Sr.") == "Robert Jones"
        assert standardizer.standardize("Jane Doe PhD") == "Jane Doe"

    def test_middle_name_handling(self):
        """Test middle name normalization."""
        standardizer = NameStandardizer()

        # Full middle name
        result = standardizer.standardize("John Michael Smith")
        assert result == "John Michael Smith"

        # Middle initial
        result = standardizer.standardize("John M. Smith")
        assert result == "John M Smith"

    def test_hyphenated_names(self):
        """Test hyphenated name handling."""
        standardizer = NameStandardizer()

        result = standardizer.standardize("mary-jane watson")
        assert result == "Mary-Jane Watson"

    def test_apostrophe_names(self):
        """Test apostrophe name handling."""
        standardizer = NameStandardizer()

        result = standardizer.standardize("john o'brien")
        assert result == "John O'Brien"

        result = standardizer.standardize("mary d'angelo")
        assert result == "Mary D'Angelo"

    def test_mc_mac_names(self):
        """Test Mc and Mac name handling."""
        standardizer = NameStandardizer()

        result = standardizer.standardize("john mcdonald")
        assert result == "John McDonald"

        result = standardizer.standardize("robert macleod")
        assert result == "Robert Macleod"

    def test_complex_name(self):
        """Test complex name with multiple features."""
        standardizer = NameStandardizer()

        result = standardizer.standardize("Dr. Bob O'Brien Jr.")
        assert result == "Robert O'Brien"

    def test_age_removal(self):
        """Test removal of age in parentheses."""
        standardizer = NameStandardizer()

        result = standardizer.standardize("John Smith (55)")
        assert result == "John Smith"

    def test_invalid_names(self):
        """Test handling of invalid names."""
        standardizer = NameStandardizer()

        assert standardizer.standardize("") is None
        assert standardizer.standardize(None) is None
        assert standardizer.standardize("   ") is None
        assert standardizer.standardize("Smith") is None  # Only last name

    def test_batch_standardization(self):
        """Test batch standardization."""
        standardizer = NameStandardizer()

        names = [
            "Bob Smith",
            "Dr. Jane Doe",
            "Bill O'Brien Jr."
        ]

        result = standardizer.standardize_batch(names)

        assert result["Bob Smith"] == "Robert Smith"
        assert result["Dr. Jane Doe"] == "Jane Doe"
        assert result["Bill O'Brien Jr."] == "William O'Brien"

    def test_convenience_function(self):
        """Test convenience function."""
        result = standardize_name("Bob Smith")
        assert result == "Robert Smith"

    def test_no_nickname_expansion(self):
        """Test with nickname expansion disabled."""
        standardizer = NameStandardizer(expand_nicknames=False)

        result = standardizer.standardize("Bob Smith")
        assert result == "Bob Smith"

    def test_no_title_removal(self):
        """Test with title removal disabled."""
        standardizer = NameStandardizer(remove_titles=False)

        result = standardizer.standardize("Dr. John Smith")
        # Title stays but gets capitalized
        assert "Dr" in result or "Dr." in result

    def test_case_insensitivity(self):
        """Test case insensitive processing."""
        standardizer = NameStandardizer()

        result1 = standardizer.standardize("JOHN SMITH")
        result2 = standardizer.standardize("john smith")
        result3 = standardizer.standardize("John Smith")

        assert result1 == result2 == result3 == "John Smith"
